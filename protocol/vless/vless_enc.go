//go:build with_vless_enc

// Fork-owned glue between the upstream-owned VLESS outbound and the
// encryption layer (MUTS-10). Ported from sing-box-lx v1.14.0-lx.26
// protocol/vless/lx_encryption.go (commits 57ece01c + d1c2f3e2). Everything
// the upstream file needs is a call into this file from inside fork-patch
// markers.
package vless

import (
	"context"
	"net"
	"time"

	"github.com/sagernet/sing-box/protocol/vless/encryption"
	"github.com/sagernet/sing/common"
	E "github.com/sagernet/sing/common/exceptions"
)

// initVLESSEncryption configures the post-quantum encryption layer from the
// outbound's `encryption` spec string. "none" (and empty) leave the layer
// off; anything else is parsed and initialized here so a malformed spec
// fails at config time, not at first dial.
func initVLESSEncryption(outbound *Outbound, spec string) error {
	if spec == "" || spec == "none" {
		return nil
	}
	instance, err := encryption.NewInstance(spec)
	if err != nil {
		return E.Cause(err, "parse encryption")
	}
	outbound.encryption = instance
	return nil
}

// wrapEncryption performs the post-quantum handshake over an already-dialed
// conn, returning it unchanged when the layer is not configured. It sits above
// the transport/TLS and below the vless client, which stays unaware of it.
// A failed handshake closes the conn: the caller only propagates the error.
//
// Handshake takes a bare net.Conn (the wire format is fixed by upstream Xray,
// so it grows no context parameter) and internally writes fragmented padding
// with sleeps in between. On a half-alive node those writes block forever,
// which is how URL tests turned into goroutines that outlived the box. The
// dial deadline is therefore applied to the conn for the duration of the
// handshake and cleared afterwards, so the caller's context governs it.
//
// WRITE side only, deliberately (lx d1c2f3e2). The hang this guards against
// is a blocked Write into an upload body nobody reads, so a read deadline
// buys nothing here — and it would cost correctness: an XHTTP read deadline
// is one-shot (it closes the late-bound download body, and clearing it cannot
// reopen that), so a handshake that overran the dial deadline but still
// succeeded would hand back a conn whose download side is already dead.
// SetDeadline covers both directions, hence the narrower call.
func (h *vlessDialer) wrapEncryption(ctx context.Context, conn net.Conn) (net.Conn, error) {
	if h.encryption == nil {
		return conn, nil
	}
	if deadline, ok := ctx.Deadline(); ok {
		if err := conn.SetWriteDeadline(deadline); err == nil {
			defer conn.SetWriteDeadline(time.Time{})
		}
	}
	encryptedConn, err := h.encryption.Handshake(conn)
	if err != nil {
		common.Close(conn)
		return nil, E.Cause(err, "encryption handshake")
	}
	return encryptedConn, nil
}
