#!/usr/bin/env python3
"""MUTS-11 interoperability hard gate runner (Python standard library only)."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, platform, re, shutil, subprocess, tempfile, time, uuid
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import configs
import infra
import yamlmini

XRAY_VERSION = "v26.7.28"
MIHOMO_VERSION = "v1.19.30"
XRAY_URL = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_VERSION}/Xray-linux-64.zip"
XRAY_SHA256 = "8195d909f1109b8f3d99eefe401a3c451d7bf4af71f24d3815420f77e5dd2a40"
MIHOMO_URL = f"https://github.com/MetaCubeX/mihomo/releases/download/{MIHOMO_VERSION}/mihomo-linux-amd64-{MIHOMO_VERSION}.gz"
MIHOMO_SHA256 = "cf06ce2c7d1421bdbda14ee4a5b6046672dc35ebf8eecd8e77504ec3c0ed9a84"
FORK_TAGS = "with_xhttp,with_vless_enc,with_utls"
PAYLOAD_SIZE = 10 * 1024 * 1024
XHTTP_MODES = ("auto", "packet-up", "stream-up", "stream-one")

@dataclass(frozen=True)
class Row:
    name: str
    tags: str = "both"
    required: bool = True

def required_rows() -> list[Row]:
    rows = [Row("build-tags-off", "tags-off"), Row("build-tags-on", "tags-on")]
    rows += [Row(f"xhttp-{m}-{tls}") for m in XHTTP_MODES for tls in ("tls", "reality")]
    rows += [Row(f"vless-enc-fork-to-xray-{mode}") for mode in ("none", "1rtt", "0rtt")]
    rows += [Row(f"mihomo-to-xray-{mode}") for mode in ("1rtt", "0rtt")]
    rows += [Row(f"xray-to-mihomo-{mode}") for mode in ("1rtt", "0rtt")]
    rows += [Row("tags-off-upstream-check", "tags-off")]
    rows += [Row(f"tags-off-{transport}-loopback-download", "tags-off") for transport in ("ws", "grpc", "httpupgrade")]
    return rows

def make_uuid(seed: str = "muts-11") -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

def deterministic_payload(path: Path, size: int = PAYLOAD_SIZE) -> str:
    block = hashlib.sha256(b"MUTS-11 deterministic payload\n").digest()
    with path.open("wb") as out:
        for offset in range(0, size, 1 << 20):
            n = min(1 << 20, size - offset); out.write((block * ((n + len(block) - 1) // len(block)))[:n])
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_xray_keys(output: str) -> dict[str, str]:
    """Parse the stable labels emitted by `xray x25519`."""
    values = {}
    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip().lower().replace(" ", "_")] = value.strip()
    private = values.get("privatekey") or values.get("private_key")
    public = values.get("password_(publickey)") or values.get("publickey") or values.get("public_key")
    if not private or not public:
        raise RuntimeError("xray x25519 output did not contain private/public keys")
    return {"private_key": private, "public_key": public}


def parse_vless_enc(output: str) -> list[tuple[str, str]]:
    """Return the X25519 and ML-KEM decryption/encryption pairs from `xray vlessenc`."""
    decryptions = re.findall(r'"decryption":\s*"([^"]+)"', output)
    encryptions = re.findall(r'"encryption":\s*"([^"]+)"', output)
    pairs = list(zip(decryptions, encryptions))
    if not pairs:
        raise RuntimeError("xray vlessenc emitted no key pairs")
    return pairs

def provenance(root: Path) -> dict[str, str]:
    try: commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception: commit = "unknown"
    return {"commit": commit, "xray": XRAY_VERSION, "mihomo": MIHOMO_VERSION, "python": platform.python_version(), "platform": platform.platform()}


class Runner:
    def __init__(self, results: Path):
        self.results = results
        self.results.mkdir(parents=True, exist_ok=True)
        self.rows = []

    def add(self, row: Row, status: str, started: float, command=(), config="", log="", error="", evidence=None):
        self.rows.append({"row": row.name, "required": row.required, "status": status, "duration_seconds": round(time.monotonic()-started, 3), "command": list(command), "config": str(config), "log": str(log), "error": error, "evidence": evidence or {}})

    def write(self, provenance_data):
        passed = len(self.rows) == len(required_rows()) and all(x["status"] == "PASS" for x in self.rows if x["required"])
        data = {"provenance": provenance_data, "rows": self.rows, "passed": passed}
        (self.results / "interop.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        md = ["# MUTS-11 interoperability report", "", f"Hard gate: **{'PASS' if passed else 'FAIL'}**", "", "| Row | Status | Duration | Evidence |", "|---|---|---:|---|"]
        md += [f"| `{x['row']}` | **{x['status']}** | {x['duration_seconds']}s | `{x['config'] or x['log'] or ' '.join(x['command'])}` {x['error']} |" for x in self.rows]
        (self.results / "interop.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return passed

def self_test() -> int:
    assert len(required_rows()) == 21
    assert [x.name for x in required_rows()[2:10]] == [f"xhttp-{m}-{t}" for m in XHTTP_MODES for t in ("tls", "reality")]
    assert required_rows()[0].name == "build-tags-off" and required_rows()[1].name == "build-tags-on"
    assert make_uuid() == make_uuid()
    assert parse_xray_keys("PrivateKey: a\nPassword (PublicKey): b\n") == {"private_key": "a", "public_key": "b"}
    configs.self_check()
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "fixture.bin"
        digest = deterministic_payload(p, 4096)
        assert digest == infra.sha256_file(p)
        assert "mixed-port:" in yamlmini.dumps(configs.mihomo_vless_encryption_client("127.0.0.1", 1, make_uuid(), "none"))
        runner = Runner(Path(d) / "results")
        runner.add(required_rows()[0], "FAIL", time.monotonic(), error="expected")
        assert not runner.write({})
    print("self-test: PASS")
    return 0


def _write_config(path: Path, value: object, mihomo: bool = False) -> Path:
    configs.validate_no_placeholders(value)
    if mihomo:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yamlmini.dumps(value) + "\n", encoding="utf-8")
        return path
    return infra.write_json(path, value)


def _record_failure(runner: Runner, row: Row, started: float, row_dir: Path, exc: Exception) -> None:
    error = f"{type(exc).__name__}: {exc}"
    (row_dir / "failure.txt").write_text(error + "\n", encoding="utf-8")
    runner.add(row, "FAIL", started, config=row_dir, log=row_dir / "failure.txt", error=error)


def _exercise_pair(server_bin: Path, server_config: Path, server_port: int, client_bin: Path,
                   client_config: Path, proxy_port: int, fixture_port: int, fixture_sha: str,
                   row_dir: Path) -> None:
    if not server_bin.name.lower().startswith("mihomo"):
        infra.run(infra.checked_config_command(server_bin, server_config), log=row_dir / "server-check.log")
    if not client_bin.name.lower().startswith("mihomo"):
        infra.run(infra.checked_config_command(client_bin, client_config), log=row_dir / "client-check.log")
    with ExitStack() as stack:
        stack.enter_context(infra.managed_process(infra.run_config_command(server_bin, server_config), row_dir / "server.log", server_port))
        stack.enter_context(infra.managed_process(infra.run_config_command(client_bin, client_config), row_dir / "client.log", proxy_port))
        infra.proxy_download(shutil.which("curl") or "curl", proxy_port, fixture_port, fixture_sha,
                             row_dir / "fixture.bin", row_dir / "curl.log")


def _prepare(root: Path, work: Path, results: Path) -> dict[str, object]:
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise RuntimeError("full interoperability execution requires Linux/amd64")
    for command in ("go", "git", "curl"):
        if shutil.which(command) is None:
            raise RuntimeError(f"missing prerequisite: {command}")
    tools = work / "tools"
    xray = infra.acquire_binary("XRAY_BIN", XRAY_URL, XRAY_SHA256, "xray", tools)
    mihomo = infra.acquire_binary("MIHOMO_BIN", MIHOMO_URL, MIHOMO_SHA256, "mihomo", tools)
    binaries = work / "bin"
    binaries.mkdir()
    fork_off = Path(os.environ.get("SING_BOX_OFF_BIN", binaries / "sing-box-off"))
    fork_on = Path(os.environ.get("SING_BOX_BIN", binaries / "sing-box-on"))
    upstream = Path(os.environ.get("UPSTREAM_SING_BOX_BIN", binaries / "sing-box-upstream"))
    if not fork_off.exists():
        infra.run(["go", "build", "-trimpath", "-o", str(fork_off), "./cmd/sing-box"], cwd=root, log=results / "build-tags-off.log")
    if not fork_on.exists():
        infra.run(["go", "build", "-trimpath", "-tags", FORK_TAGS, "-o", str(fork_on), "./cmd/sing-box"], cwd=root, log=results / "build-tags-on.log")
    if not upstream.exists():
        upstream_checkout = work / "upstream"
        infra.run(["git", "clone", "--depth", "1", "--branch", "v1.13.19", "https://github.com/SagerNet/sing-box", str(upstream_checkout)], log=results / "upstream-clone.log")
        infra.run(["go", "build", "-trimpath", "-o", str(upstream), "./cmd/sing-box"], cwd=upstream_checkout, log=results / "build-upstream.log")
    cert_prefix = work / "fixture"
    infra.run([str(xray), "tls", "cert", "--domain", "localhost", "--name", "localhost", "--file", str(cert_prefix), "--json=false"], log=results / "certificate.log")
    reality = parse_xray_keys(infra.run([str(xray), "x25519"], log=results / "reality-keys.log"))
    encryption_pairs = parse_vless_enc(infra.run([str(xray), "vlessenc"], log=results / "vlessenc.log"))
    fixture_root = work / "fixture-root"
    fixture_root.mkdir()
    fixture_sha = deterministic_payload(fixture_root / "fixture.bin")
    fixture_port = infra.free_port()
    server_script = infra.write_https_server(work / "https_server.py")
    fixture_context = infra.managed_process([shutil.which("python3") or shutil.which("python") or "python3", str(server_script), "--port", str(fixture_port), "--root", str(fixture_root), "--cert", str(cert_prefix) + ".crt", "--key", str(cert_prefix) + ".key"], results / "fixture-server.log", fixture_port)
    return {"xray": xray, "mihomo": mihomo, "fork_off": fork_off, "fork_on": fork_on, "upstream": upstream,
            "cert": Path(str(cert_prefix) + ".crt"), "key": Path(str(cert_prefix) + ".key"), "reality": reality,
            "enc_pair": encryption_pairs[-1], "fixture_port": fixture_port, "fixture_sha": fixture_sha,
            "fixture_context": fixture_context}


def full_run(root: Path, results: Path) -> int:
    runner = Runner(results)
    try:
        with tempfile.TemporaryDirectory(prefix="muts11-") as temporary:
            env = _prepare(root, Path(temporary), results)
            with env["fixture_context"]:
                for row in required_rows():
                    started = time.monotonic()
                    row_dir = results / row.name
                    row_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        uuid_value = make_uuid()
                        server_port, proxy_port = infra.free_port(), infra.free_port()
                        if row.name == "build-tags-off":
                            infra.run([str(env["fork_off"]), "version"], log=row_dir / "version.log")
                            runner.add(row, "PASS", started, config=row_dir, evidence={"binary": str(env["fork_off"])})
                            continue
                        if row.name == "build-tags-on":
                            infra.run([str(env["fork_on"]), "version"], log=row_dir / "version.log")
                            runner.add(row, "PASS", started, config=row_dir, evidence={"binary": str(env["fork_on"]), "tags": FORK_TAGS})
                            continue
                        if row.name.startswith("xhttp-"):
                            parts = row.name.split("-")
                            mode, security = "-".join(parts[1:-1]), parts[-1]
                            reality = security == "reality"
                            server = configs.xray_vless_server(server_port, uuid_value, mode=mode, reality=reality,
                                cert_path=str(env["cert"]), key_path=str(env["key"]), reality_private_key=env["reality"]["private_key"],
                                reality_handshake_port=env["fixture_port"])
                            client = configs.sing_box_vless_xhttp_client("127.0.0.1", server_port, uuid_value, mode=mode, reality=reality,
                                reality_public_key=env["reality"]["public_key"], mixed_proxy_port=proxy_port)
                            server_cfg = _write_config(row_dir / "xray-server.json", server)
                            client_cfg = _write_config(row_dir / "sing-box-client.json", client)
                            _exercise_pair(env["xray"], server_cfg, server_port, env["fork_on"], client_cfg, proxy_port, env["fixture_port"], env["fixture_sha"], row_dir)
                        elif row.name.startswith("vless-enc-fork-to-xray-"):
                            mode = row.name.rsplit("-", 1)[-1]
                            decryption, encryption0 = env["enc_pair"]
                            encryption = "none" if mode == "none" else encryption0.replace(".0rtt.", f".{mode}.")
                            server_cfg = _write_config(row_dir / "xray-server.json", configs.xray_vless_encryption_server(server_port, uuid_value, "none" if mode == "none" else decryption))
                            client_cfg = _write_config(row_dir / "sing-box-client.json", configs.sing_box_vless_encryption_client("127.0.0.1", server_port, uuid_value, encryption, proxy_port))
                            _exercise_pair(env["xray"], server_cfg, server_port, env["fork_on"], client_cfg, proxy_port, env["fixture_port"], env["fixture_sha"], row_dir)
                        elif row.name.startswith("mihomo-to-xray-"):
                            mode = row.name.rsplit("-", 1)[-1]
                            decryption, encryption0 = env["enc_pair"]
                            encryption = encryption0.replace(".0rtt.", f".{mode}.")
                            server_cfg = _write_config(row_dir / "xray-server.json", configs.xray_vless_encryption_server(server_port, uuid_value, decryption))
                            client_cfg = _write_config(row_dir / "mihomo-client.yaml", configs.mihomo_vless_encryption_client("127.0.0.1", server_port, uuid_value, encryption, proxy_port), True)
                            _exercise_pair(env["xray"], server_cfg, server_port, env["mihomo"], client_cfg, proxy_port, env["fixture_port"], env["fixture_sha"], row_dir)
                        elif row.name.startswith("xray-to-mihomo-"):
                            mode = row.name.rsplit("-", 1)[-1]
                            decryption, encryption0 = env["enc_pair"]
                            encryption = encryption0.replace(".0rtt.", f".{mode}.")
                            server_cfg = _write_config(row_dir / "mihomo-server.yaml", configs.mihomo_vless_encryption_listener(server_port, uuid_value, decryption), True)
                            client_cfg = _write_config(row_dir / "xray-client.json", configs.xray_vless_encryption_client("127.0.0.1", server_port, uuid_value, encryption, proxy_port))
                            _exercise_pair(env["mihomo"], server_cfg, server_port, env["xray"], client_cfg, proxy_port, env["fixture_port"], env["fixture_sha"], row_dir)
                        elif row.name == "tags-off-upstream-check":
                            for binary, label in ((env["fork_off"], "fork"), (env["upstream"], "upstream")):
                                infra.run([str(binary), "check", "-c", str(root / "fork-test/config/smoke_server.json")], log=row_dir / f"{label}-server-check.log")
                                infra.run([str(binary), "check", "-c", str(root / "fork-test/config/smoke_client.json")], log=row_dir / f"{label}-client-check.log")
                            infra.run(["go", "vet", "./..."], cwd=root, log=row_dir / "go-vet.log")
                            infra.run(["go", "test", "./..."], cwd=root, log=row_dir / "go-test.log")
                        else:
                            transport = row.name.removeprefix("tags-off-").removesuffix("-loopback-download")
                            server_cfg = _write_config(row_dir / "server.json", configs.sing_box_loopback_server(server_port, uuid_value, transport))
                            for binary, label in ((env["fork_off"], "fork"), (env["upstream"], "upstream")):
                                client_port = infra.free_port()
                                client_cfg = _write_config(row_dir / f"{label}-client.json", configs.sing_box_loopback_client("127.0.0.1", server_port, uuid_value, transport, client_port))
                                with infra.managed_process(infra.run_config_command(env["fork_off"], server_cfg), row_dir / f"{label}-server.log", server_port):
                                    with infra.managed_process(infra.run_config_command(binary, client_cfg), row_dir / f"{label}-client.log", client_port):
                                        infra.proxy_download(shutil.which("curl") or "curl", client_port, env["fixture_port"], env["fixture_sha"], row_dir / f"{label}-fixture.bin", row_dir / f"{label}-curl.log")
                        runner.add(row, "PASS", started, config=row_dir, evidence={"fixture_sha256": env["fixture_sha"], "fixture_bytes": PAYLOAD_SIZE})
                    except Exception as exc:
                        _record_failure(runner, row, started, row_dir, exc)
    except Exception as exc:
        for row in required_rows():
            if not any(result["row"] == row.name for result in runner.rows):
                row_dir = results / row.name
                row_dir.mkdir(parents=True, exist_ok=True)
                _record_failure(runner, row, time.monotonic(), row_dir, exc)
    return 0 if runner.write(provenance(root)) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--results", type=Path, default=Path("fork-test/interop/results"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.plan:
        for row in required_rows():
            print(f"{row.name}\t{row.tags}\t{'required' if row.required else 'optional'}")
        return 0
    return full_run(args.root.resolve(), args.results.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
