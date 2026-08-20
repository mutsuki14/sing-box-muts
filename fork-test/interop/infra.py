"""Execution primitives for the MUTS-11 Linux interoperability harness."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: Sequence[str], *, cwd: Path | None = None, timeout: int = 900, log: Path | None = None) -> str:
    """Run one command, optionally preserving merged output, and fail verbosely."""
    completed = subprocess.run(list(command), cwd=cwd, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=timeout, check=False)
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"command exited {completed.returncode}: {' '.join(command)}\n{completed.stdout[-4000:]}")
    return completed.stdout


def checked_config_command(binary: Path, config: Path) -> list[str]:
    """Return the Xray/sing-box command used to validate a generated config."""
    if binary.name.lower().startswith("xray"):
        return [str(binary), "run", "-test", "-config", str(config)]
    return [str(binary), "check", "-c", str(config)]

def run_config_command(binary: Path, config: Path) -> list[str]:
    """Return the long-running command for an Xray, mihomo, or sing-box config."""
    name = binary.name.lower()
    if name.startswith("xray"):
        return [str(binary), "run", "-config", str(config)]
    if name.startswith("mihomo"):
        return [str(binary), "-f", str(config)]
    return [str(binary), "run", "-c", str(config)]


def acquire_binary(env_name: str, url: str, checksum: str, archive_member: str, tools: Path) -> Path:
    """Use an explicit binary override or download and verify a pinned release asset."""
    override = os.environ.get(env_name)
    if override:
        binary = Path(override).resolve()
        if not binary.is_file():
            raise RuntimeError(f"{env_name} does not name a file: {binary}")
        return binary
    tools.mkdir(parents=True, exist_ok=True)
    archive = tools / Path(url).name
    if not archive.exists():
        urllib.request.urlretrieve(url, archive)
    actual = sha256_file(archive)
    if actual != checksum:
        raise RuntimeError(f"SHA256 mismatch for {archive.name}: expected {checksum}, got {actual}")
    target = tools / Path(archive_member).name
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            with bundle.open(archive_member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    elif archive.suffix == ".gz":
        with gzip.open(archive, "rb") as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
    else:
        raise RuntimeError(f"unsupported archive: {archive}")
    target.chmod(0o755)
    return target


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_tcp(port: int, process: subprocess.Popen[bytes], timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"process exited before port {port} became ready (status {process.returncode})")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"timeout waiting for TCP port {port}")


@contextmanager
def managed_process(command: Sequence[str], log_path: Path, ready_port: int, *, cwd: Path | None = None) -> Iterator[subprocess.Popen[bytes]]:
    """Start one process group, prove readiness, and always terminate the group."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as output:
        process = subprocess.Popen(list(command), cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=(os.name != "nt"), creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0))
        try:
            wait_tcp(ready_port, process)
            yield process
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        process.kill()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)


def write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def proxy_download(curl: str, proxy_port: int, fixture_port: int, expected_sha256: str,
                   output: Path, log: Path) -> None:
    """Fetch by hostname through SOCKS remote DNS and verify fixture integrity."""
    command = [curl, "--fail", "--silent", "--show-error", "--insecure", "--max-time", "120",
               "--socks5-hostname", f"127.0.0.1:{proxy_port}",
               f"https://localhost:{fixture_port}/fixture.bin", "--output", str(output)]
    run(command, timeout=150, log=log)
    size = output.stat().st_size
    if size < 10 * 1024 * 1024:
        raise RuntimeError(f"download too small: {size} bytes")
    actual = sha256_file(output)
    if actual != expected_sha256:
        raise RuntimeError(f"payload SHA256 mismatch: expected {expected_sha256}, got {actual}")
    output.unlink()


def write_https_server(path: Path) -> Path:
    path.write_text("""import argparse, http.server, ssl\np=argparse.ArgumentParser(); p.add_argument('--port',type=int); p.add_argument('--root'); p.add_argument('--cert'); p.add_argument('--key'); a=p.parse_args()\nhandler=lambda *x,**k: http.server.SimpleHTTPRequestHandler(*x,directory=a.root,**k)\ns=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),handler); c=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); c.load_cert_chain(a.cert,a.key); s.socket=c.wrap_socket(s.socket,server_side=True); print('ready',flush=True); s.serve_forever()\n""", encoding="utf-8")
    return path
