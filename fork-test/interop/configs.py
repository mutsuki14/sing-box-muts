"""Deterministic configuration factories for the MUTS-11 interop matrix.

The module deliberately returns plain dictionaries.  It has no dependency on the
runner or on a YAML/JSON package; callers can serialize the result with their
product's serializer.
"""
from __future__ import annotations

from typing import Any


_MODES = ("auto", "packet-up", "stream-up", "stream-one")
_LOOPBACK = ("ws", "grpc", "httpupgrade")


def _port(value: int, name: str = "port") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
        raise ValueError(f"{name} must be an integer between 1 and 65535")
    return value


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _mode(mode: str) -> str:
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}, got {mode!r}")
    return mode


def _tls_xray(cert_path: str, key_path: str, server_name: str) -> dict[str, Any]:
    return {
        "serverName": _text(server_name, "server_name"),
        "alpn": ["h2", "http/1.1"],
        "certificates": [{"certificateFile": _text(cert_path, "cert_path"), "keyFile": _text(key_path, "key_path")}],
    }


def _xray_xhttp(path: str, mode: str) -> dict[str, Any]:
    return {"network": "xhttp", "xhttpSettings": {"path": _text(path, "path"), "mode": _mode(mode)}}


def xray_vless_server(
    port: int,
    client_uuid: str,
    mode: str = "auto",
    reality: bool = False,
    cert_path: str = "fixture.crt",
    key_path: str = "fixture.key",
    reality_private_key: str | None = None,
    reality_short_id: str = "0123456789abcdef",
    reality_server_name: str = "localhost",
    reality_handshake_address: str = "127.0.0.1",
    reality_handshake_port: int | None = None,
    path: str = "/muts",
    decryption: str = "none",
    fixture_host: str = "127.0.0.1",
    fixture_port: int | None = None,
) -> dict[str, Any]:
    """Return an Xray VLESS XHTTP server (TLS or REALITY)."""
    _port(port); _text(client_uuid, "client_uuid"); _mode(mode); _text(fixture_host, "fixture_host")
    if fixture_port is not None: _port(fixture_port, "fixture_port")
    stream = _xray_xhttp(path, mode)
    if reality:
        private = _text(reality_private_key or "", "reality_private_key")
        short_id = _text(reality_short_id, "reality_short_id")
        hp = _port(reality_handshake_port if reality_handshake_port is not None else port, "reality_handshake_port")
        stream.update({"security": "reality", "realitySettings": {
            "target": f"{_text(reality_handshake_address, 'reality_handshake_address')}:{hp}",
            "serverNames": [_text(reality_server_name, "reality_server_name")],
            "privateKey": private,
            "shortIds": [short_id],
        }})
    else:
        stream.update({"security": "tls", "tlsSettings": _tls_xray(cert_path, key_path, reality_server_name)})
    return {"log": {"loglevel": "warning"}, "inbounds": [{
        "listen": "127.0.0.1", "port": port, "protocol": "vless",
        "settings": {"clients": [{"id": client_uuid}], "decryption": _text(decryption, "decryption")},
        "streamSettings": stream,
    }], "outbounds": [{"protocol": "freedom"}]}


def xray_vless_client(
    address: str, port: int, client_uuid: str, mode: str = "auto", reality: bool = False,
    cert_path: str = "fixture.crt", key_path: str = "fixture.key",
    reality_public_key: str | None = None, reality_short_id: str = "0123456789abcdef",
    server_name: str = "localhost", path: str = "/muts", encryption: str = "none",
    mixed_proxy_port: int = 10808,
) -> dict[str, Any]:
    """Return an Xray client with a local SOCKS inbound and direct fallback."""
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port"); _mode(mode)
    stream = _xray_xhttp(path, mode)
    if reality:
        stream.update({"security": "reality", "realitySettings": {"serverName": _text(server_name, "server_name"), "publicKey": _text(reality_public_key or "", "reality_public_key"), "shortId": _text(reality_short_id, "reality_short_id")}})
    else:
        stream.update({"security": "tls", "tlsSettings": {"serverName": _text(server_name, "server_name"), "allowInsecure": True, "alpn": ["h2", "http/1.1"]}})
    return {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "127.0.0.1", "port": mixed_proxy_port, "protocol": "mixed", "settings": {"auth": "noauth", "udp": True}}], "outbounds": [{
        "protocol": "vless", "settings": {"vnext": [{"address": address, "port": port, "users": [{"id": client_uuid, "encryption": _text(encryption, "encryption")}]}]}, "streamSettings": stream,
    }, {"protocol": "freedom", "tag": "direct"}], "routing": {"domainStrategy": "AsIs", "rules": []}}


def xray_vless_encryption_server(port: int, client_uuid: str, decryption: str, listen: str = "127.0.0.1", fixture_host: str = "127.0.0.1", fixture_port: int | None = None) -> dict[str, Any]:
    """Return a plain Xray VLESS encryption server without TLS or XHTTP."""
    _port(port); _text(client_uuid, "client_uuid"); _text(listen, "listen"); _text(fixture_host, "fixture_host")
    if fixture_port is not None: _port(fixture_port, "fixture_port")
    return {"log": {"loglevel": "warning"}, "inbounds": [{"listen": listen, "port": port, "protocol": "vless", "settings": {"clients": [{"id": client_uuid}], "decryption": _text(decryption, "decryption")}}], "outbounds": [{"protocol": "freedom"}]}


def xray_vless_encryption_client(address: str, port: int, client_uuid: str, encryption: str, mixed_proxy_port: int = 10808) -> dict[str, Any]:
    """Return a plain Xray VLESS encryption client without TLS or XHTTP."""
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port")
    return {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "127.0.0.1", "port": mixed_proxy_port, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}], "outbounds": [{"protocol": "vless", "settings": {"vnext": [{"address": address, "port": port, "users": [{"id": client_uuid, "encryption": _text(encryption, "encryption")}]}]}}, {"protocol": "freedom", "tag": "direct"}], "routing": {"domainStrategy": "AsIs", "rules": []}}


def sing_box_vless_xhttp_client(
    address: str, port: int, client_uuid: str, mode: str = "auto", reality: bool = False,
    reality_public_key: str | None = None, reality_short_id: str = "0123456789abcdef",
    server_name: str = "localhost", path: str = "/muts", mixed_proxy_port: int = 10808,
) -> dict[str, Any]:
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port"); _mode(mode)
    tls: dict[str, Any] = {"enabled": True, "server_name": _text(server_name, "server_name"), "insecure": True}
    if reality:
        tls["utls"] = {"enabled": True, "fingerprint": "chrome"}
        tls["reality"] = {"enabled": True, "public_key": _text(reality_public_key or "", "reality_public_key"), "short_id": _text(reality_short_id, "reality_short_id")}
    return {"log": {"level": "warn"}, "inbounds": [{"type": "mixed", "tag": "in-mixed", "listen": "127.0.0.1", "listen_port": mixed_proxy_port}], "outbounds": [{"type": "vless", "tag": "proxy", "server": address, "server_port": port, "uuid": client_uuid, "tls": tls, "transport": {"type": "xhttp", "path": _text(path, "path"), "mode": mode}}, {"type": "direct", "tag": "direct"}], "route": {"final": "proxy"}}


def sing_box_vless_encryption_client(address: str, port: int, client_uuid: str, encryption: str, mixed_proxy_port: int = 10808, tls: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a plain VLESS outbound with optional protocol-level encryption."""
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port")
    spec = _text(encryption, "encryption")
    if spec != "none" and not spec.startswith("mlkem768x25519plus."):
        raise ValueError("encryption must be none or a mlkem768x25519plus spec")
    outbound: dict[str, Any] = {"type": "vless", "tag": "proxy", "server": address, "server_port": port, "uuid": client_uuid}
    if spec != "none":
        outbound["encryption"] = spec
    if tls is not None:
        outbound["tls"] = dict(tls)
    return {"log": {"level": "warn"}, "inbounds": [{"type": "mixed", "tag": "in-mixed", "listen": "127.0.0.1", "listen_port": mixed_proxy_port}], "outbounds": [outbound, {"type": "direct", "tag": "direct"}], "route": {"final": "proxy"}}


def mihomo_vless_xhttp_client(address: str, port: int, client_uuid: str, mode: str = "auto", mixed_proxy_port: int = 10809, server_name: str = "localhost", path: str = "/muts", reality: bool = False, reality_public_key: str | None = None, reality_short_id: str = "0123456789abcdef") -> dict[str, Any]:
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port"); _mode(mode)
    proxy: dict[str, Any] = {"name": "muts", "type": "vless", "server": address, "port": port, "uuid": client_uuid, "tls": True, "servername": _text(server_name, "server_name"), "network": "xhttp", "xhttp-opts": {"path": _text(path, "path"), "mode": mode}}
    if reality:
        proxy["client-fingerprint"] = "chrome"; proxy["reality-opts"] = {"public-key": _text(reality_public_key or "", "reality_public_key"), "short-id": _text(reality_short_id, "reality_short_id")}
    return {"mixed-port": mixed_proxy_port, "allow-lan": False, "proxies": [proxy], "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": ["muts"]}], "rules": ["MATCH,PROXY"]}

def mihomo_vless_encryption_client(address: str, port: int, client_uuid: str, encryption: str, mixed_proxy_port: int = 10809) -> dict[str, Any]:
    """Return a plain mihomo VLESS encryption client without XHTTP options."""
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port")
    spec = _text(encryption, "encryption")
    if spec != "none" and not spec.startswith("mlkem768x25519plus."):
        raise ValueError("encryption must be none or a mlkem768x25519plus spec")
    proxy: dict[str, Any] = {"name": "muts", "type": "vless", "server": address, "port": port, "uuid": client_uuid}
    if spec != "none":
        proxy["encryption"] = spec
    return {"mixed-port": mixed_proxy_port, "allow-lan": False, "proxies": [proxy], "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": ["muts"]}], "rules": ["MATCH,PROXY"]}


def mihomo_vless_encryption_listener(listen_port: int, client_uuid: str, decryption: str, listen: str = "127.0.0.1", fixture_host: str = "127.0.0.1", fixture_port: int | None = None) -> dict[str, Any]:
    """Return a plain mihomo VLESS listener with inbound decryption."""
    _text(listen, "listen"); _port(listen_port, "listen_port"); _text(client_uuid, "client_uuid"); _text(decryption, "decryption"); _text(fixture_host, "fixture_host")
    if fixture_port is not None: _port(fixture_port, "fixture_port")
    return {"listeners": [{"name": "muts", "type": "vless", "listen": listen, "port": listen_port, "users": [{"uuid": client_uuid}], "decryption": decryption}], "rules": ["MATCH,DIRECT"]}


def _transport(kind: str, path: str, service_name: str) -> dict[str, Any]:
    if kind not in _LOOPBACK: raise ValueError(f"transport must be one of {_LOOPBACK}, got {kind!r}")
    if kind == "ws": return {"type": "ws", "path": path}
    if kind == "grpc": return {"type": "grpc", "service_name": service_name}
    return {"type": "httpupgrade", "path": path}


def sing_box_loopback_server(port: int, client_uuid: str, transport: str, path: str = "/muts", service_name: str = "muts", listen: str = "127.0.0.1", fixture_host: str = "127.0.0.1", fixture_port: int | None = None) -> dict[str, Any]:
    _port(port); _text(client_uuid, "client_uuid"); _text(path, "path"); _text(listen, "listen"); _text(fixture_host, "fixture_host")
    if fixture_port is not None: _port(fixture_port, "fixture_port")
    return {"log": {"level": "warn"}, "inbounds": [{"type": "vless", "tag": "in-vless", "listen": listen, "listen_port": port, "users": [{"uuid": client_uuid}], "transport": _transport(transport, path, service_name)}], "outbounds": [{"type": "direct", "tag": "direct"}]}


def sing_box_loopback_client(address: str, port: int, client_uuid: str, transport: str, mixed_proxy_port: int = 10808, path: str = "/muts", service_name: str = "muts") -> dict[str, Any]:
    _text(address, "address"); _port(port); _text(client_uuid, "client_uuid"); _port(mixed_proxy_port, "mixed_proxy_port")
    return {"log": {"level": "warn"}, "inbounds": [{"type": "mixed", "tag": "in-mixed", "listen": "127.0.0.1", "listen_port": mixed_proxy_port}], "outbounds": [{"type": "vless", "tag": "proxy", "server": address, "server_port": port, "uuid": client_uuid, "transport": _transport(transport, path, service_name)}, {"type": "direct", "tag": "direct"}], "route": {"final": "proxy"}}


def validate_no_placeholders(obj: Any) -> None:
    """Raise ValueError when a config contains an unresolved template token."""
    bad = ("TODO", "FIXME", "PLACEHOLDER", "GENERATED_BY", "REPLACE_ME", "<PORT>", "<UUID>", "<KEY>")
    if isinstance(obj, dict):
        for key, value in obj.items():
            validate_no_placeholders(key); validate_no_placeholders(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj: validate_no_placeholders(value)
    elif isinstance(obj, str) and any(token in obj.upper() for token in bad):
        raise ValueError(f"unresolved placeholder token in config value {obj!r}")


def self_check() -> None:
    uuid = "00000000-0000-4000-8000-000000000001"
    reality_private = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    reality_public = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    for mode in _MODES:
        cfg = xray_vless_server(18080, uuid, mode=mode, reality=False)
        assert cfg["inbounds"][0]["streamSettings"]["xhttpSettings"]["mode"] == mode
        validate_no_placeholders(cfg)
    reality = xray_vless_server(18081, uuid, reality=True, reality_private_key=reality_private, reality_short_id="abcdef0123456789")
    assert reality["inbounds"][0]["streamSettings"]["security"] == "reality"
    assert reality["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"] == ["abcdef0123456789"]
    encryption_specs = (
        "mlkem768x25519plus.native.1rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "mlkem768x25519plus.native.0rtt.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    )
    for encryption_spec in encryption_specs:
        enc_client = sing_box_vless_encryption_client("127.0.0.1", 1, uuid, encryption_spec)
        xray_enc = xray_vless_encryption_client("127.0.0.1", 1, uuid, encryption_spec)
        mihomo_enc = mihomo_vless_encryption_client("127.0.0.1", 1, uuid, encryption_spec)
        assert enc_client["outbounds"][0]["encryption"] == encryption_spec
        assert mihomo_enc["proxies"][0]["encryption"] == encryption_spec
        assert "transport" not in enc_client["outbounds"][0]
        assert "streamSettings" not in xray_enc["outbounds"][0]
        assert xray_enc["inbounds"][0]["protocol"] == "socks"
        assert "network" not in mihomo_enc["proxies"][0]
        validate_no_placeholders(enc_client); validate_no_placeholders(xray_enc); validate_no_placeholders(mihomo_enc)
    none_sing_box = sing_box_vless_encryption_client("127.0.0.1", 1, uuid, "none")
    none_mihomo = mihomo_vless_encryption_client("127.0.0.1", 1, uuid, "none")
    assert "encryption" not in none_sing_box["outbounds"][0]
    assert "encryption" not in none_mihomo["proxies"][0]
    listener = mihomo_vless_encryption_listener(18082, uuid, "mlkem768x25519plus.native.600s.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    assert listener["listeners"][0]["decryption"].startswith("mlkem768")
    assert "xhttp-config" not in listener["listeners"][0]
    validate_no_placeholders(none_sing_box); validate_no_placeholders(none_mihomo); validate_no_placeholders(listener); validate_no_placeholders(reality)
    for transport in _LOOPBACK:
        assert sing_box_loopback_server(18090, uuid, transport)["inbounds"][0]["transport"]["type"] == transport
    try:
        validate_no_placeholders({"x": "GENERATED_BY_XRAY"})
    except ValueError:
        pass
    else:
        raise AssertionError("placeholder validator did not reject token")


__all__ = [name for name in globals() if not name.startswith("_")]
