//go:build !with_vless_enc

// Fork-owned glue between the upstream-owned VLESS outbound and the
// encryption layer (MUTS-10), negative half of the build-tag pair. Without
// `with_vless_enc` no ENC code path exists: a configured `encryption` field
// fails loudly at outbound construction, and the dial path is byte-identical
// to upstream.
package vless

import (
	"context"
	"net"

	E "github.com/sagernet/sing/common/exceptions"
)

// initVLESSEncryption without the build tag rejects a configured encryption
// layer instead of silently passing traffic unencrypted. "none" and empty
// pass through, matching upstream Xray's no-op spelling.
func initVLESSEncryption(outbound *Outbound, spec string) error {
	if spec == "" || spec == "none" {
		return nil
	}
	return E.New("vless outbound `encryption` requires the `with_vless_enc` build tag; this binary was built without it (see FORK.md, MUTS-10)")
}

// wrapEncryption without the build tag is a pass-through. The field read is
// a real invariant check, not decoration: initVLESSEncryption above rejects
// every configured spec, so a non-nil field here means the wiring invariant
// was broken — fail loudly rather than skip a configured handshake.
func (h *vlessDialer) wrapEncryption(ctx context.Context, conn net.Conn) (net.Conn, error) {
	if h.encryption != nil {
		return nil, E.New("vless encryption layer configured in a binary built without `with_vless_enc` (see FORK.md, MUTS-10)")
	}
	return conn, nil
}
