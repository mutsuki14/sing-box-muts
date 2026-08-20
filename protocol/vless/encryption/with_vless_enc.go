//go:build with_vless_enc

package encryption

import (
	"context"
	"net"

	E "github.com/sagernet/sing/common/exceptions"
)

// Stub installation: the tag is on, so the feature must fail loudly rather
// than silently pass traffic unencrypted. The real mlkem768x25519plus
// handshake replaces this in MUTS-10 (ported from sing-box-lx
// protocol/vless/encryption).
func init() {
	Layer = func(ctx context.Context, conn net.Conn) (net.Conn, error) {
		return nil, E.New("vless encryption: feature not ported yet (built with `with_vless_enc`; see FORK.md, tracked in MUTS-10)")
	}
}
