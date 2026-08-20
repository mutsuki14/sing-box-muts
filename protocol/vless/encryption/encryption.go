// Package encryption is the fork-owned landing zone for the VLESS
// protocol-level encryption layer (mlkem768x25519plus, Xray-compatible),
// ported from sing-box-lx in MUTS-10. This file is compiled in every build
// configuration; the layer itself is installed only under the
// `with_vless_enc` build tag (see with_vless_enc.go / without_vless_enc.go).
package encryption

import (
	"context"
	"net"
)

// Layer, when non-nil, wraps a freshly dialed VLESS connection with the
// protocol-level encryption handshake. It is installed via init() only in
// binaries built with the `with_vless_enc` build tag; in all other builds
// it stays nil and the VLESS outbound must behave exactly like upstream.
//
// The dial-path call site and the `encryption` option field land with
// MUTS-10. Until then nothing reads Layer; it exists now so the build-tag
// wiring is part of the fork skeleton and can be verified by the build
// matrix alone.
var Layer func(ctx context.Context, conn net.Conn) (net.Conn, error)
