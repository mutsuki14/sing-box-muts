//go:build with_xhttp

package v2ray

import (
	"context"

	"github.com/sagernet/sing-box/adapter"
	"github.com/sagernet/sing-box/common/tls"
	C "github.com/sagernet/sing-box/constant"
	"github.com/sagernet/sing-box/option"
	E "github.com/sagernet/sing/common/exceptions"
	M "github.com/sagernet/sing/common/metadata"
	N "github.com/sagernet/sing/common/network"
)

// newXHTTPClientTransport is the fork skeleton stub for the XHTTP client
// transport (MUTS-9, ported from sing-box-lx's transport/v2rayxhttp). It
// recognizes the xhttp transport type and fails loudly: the feature is
// compiled in but not ported yet, so a config that asks for it must not
// silently fall back to anything else.
func newXHTTPClientTransport(ctx context.Context, dialer N.Dialer, serverAddr M.Socksaddr, options option.V2RayTransportOptions, tlsConfig tls.Config) (adapter.V2RayClientTransport, bool, error) {
	if options.Type != C.V2RayTransportTypeXHTTP {
		return nil, false, nil
	}
	return nil, true, E.New("xhttp transport: feature not ported yet (built with `with_xhttp`; see FORK.md, tracked in MUTS-9)")
}
