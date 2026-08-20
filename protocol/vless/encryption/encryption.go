// Package encryption is the fork-owned implementation of the client-side
// VLESS protocol-level encryption layer (mlkem768x25519plus,
// Xray-compatible), ported from sing-box-lx in MUTS-10.
//
// This file is compiled in every build configuration: it carries only the
// hook surface the upstream-owned VLESS outbound calls through. The layer
// itself is installed via init() only under the `with_vless_enc` build tag
// (see with_vless_enc.go / without_vless_enc.go); in all other builds
// NewInstance stays nil, no ENC code path is compiled in, and the VLESS
// outbound behaves exactly like upstream (the fork-owned stub in package
// vless rejects a configured `encryption` field loudly instead of silently
// passing traffic unencrypted).
package encryption

import (
	"net"
)

// Instance is a configured client-side VLESS encryption layer. It is built
// once per outbound from the `encryption` spec string and shared across
// dials (0-RTT session tickets are cached inside).
type Instance interface {
	// Handshake performs the mlkem768x25519plus handshake over an
	// already-dialed conn and returns the wrapped conn carrying the AEAD
	// record layer. A failed handshake must leave the conn closed by the
	// caller.
	Handshake(conn net.Conn) (net.Conn, error)
}

// NewInstance builds a client-side encryption layer from the spec string
//
//	mlkem768x25519plus.<native|xorpub|random>.<0rtt|1rtt>[.<padding>…].<key>[.<key>…]
//
// It is installed via init() only in binaries built with the
// `with_vless_enc` build tag; in all other builds it stays nil and callers
// must fail loudly rather than fall back to plaintext.
var NewInstance func(spec string) (Instance, error)
