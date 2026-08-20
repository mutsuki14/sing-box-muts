# MUTS-11 interoperability harness

## Prerequisites

Linux/amd64, Python 3.11+ (stdlib only), Go 1.25.12, `git`, `curl`, and network access to download the repository's Xray wire-reference `v26.7.28`, mihomo `v1.19.30`, and upstream sing-box `v1.13.19` sources. Xray `v26.7.28` is intentionally aligned with `docs/porting-checklist.md` and the protocol implementations' source audit, even though GitHub's release metadata currently labels it prerelease. The runner accepts `SING_BOX_BIN`, `SING_BOX_OFF_BIN`, `UPSTREAM_SING_BOX_BIN`, `XRAY_BIN`, and `MIHOMO_BIN` overrides for prebuilt binaries; downloaded release assets are verified against SHA256 pins in `run.py`.

## Use

From the repository root:

```sh
python3 fork-test/interop/run.py --plan
python3 fork-test/interop/run.py
```

`--self-test` validates deterministic fixture/config/report invariants without Go or network:

```sh
python3 fork-test/interop/run.py --self-test
```

## Matrix and hard gate

The matrix records both fork builds (tags off and `with_xhttp,with_vless_enc,with_utls`), then separately builds upstream sing-box `v1.13.19`. It covers all eight XHTTP mode/TLS combinations, VLESS ENC `none`/`1rtt`/`0rtt` from the fork to Xray, mihomo→Xray and Xray→mihomo encryption in both RTT modes, tags-off upstream checks, and WebSocket/gRPC/HTTP Upgrade behavioral-equivalence downloads through both binaries. Every interoperability/download row sends an HTTPS request for `localhost` with `curl --socks5-hostname`, proving hostname forwarding/server-side resolution, and verifies a deterministic 10 MiB payload SHA256. Rows continue after failure; setup failure marks every unexecuted required row failed; any failed or missing row makes the hard gate exit nonzero. `--plan` and `--self-test` are the only non-execution modes.

## Outputs

Reports and per-row configs/logs are written to `fork-test/interop/results/` by default (override with `--results`). `interop.json` is machine-readable and `interop.md` is the summary. Download payloads are verified then removed; generated configs and logs remain as row evidence. Tool binaries, certificates, keys, and the fixture live in an isolated temporary directory and are removed after execution.

Pinned provenance records Xray `v26.7.28`, mihomo `v1.19.30`, Python, platform, and repository commit.
