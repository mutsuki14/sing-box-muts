//go:build with_xhttp

package v2ray

import (
	"context"

	"github.com/sagernet/sing-box/adapter"
	"github.com/sagernet/sing-box/common/tls"
	C "github.com/sagernet/sing-box/constant"
	"github.com/sagernet/sing-box/option"
	"github.com/sagernet/sing-box/transport/v2rayxhttp"
	M "github.com/sagernet/sing/common/metadata"
	N "github.com/sagernet/sing/common/network"
)

// newXHTTPClientTransport is the with_xhttp half of the fork hook pair: it
// recognizes the xhttp transport type and constructs the real XHTTP client
// transport (MUTS-9, ported from sing-box-lx's transport/v2rayxhttp and
// re-audited against XTLS/Xray-core v26.3.27). Without the tag the stub half
// declines and dispatch falls through to the upstream unknown-type error.
func newXHTTPClientTransport(ctx context.Context, dialer N.Dialer, serverAddr M.Socksaddr, options option.V2RayTransportOptions, tlsConfig tls.Config) (adapter.V2RayClientTransport, bool, error) {
	if options.Type != C.V2RayTransportTypeXHTTP {
		return nil, false, nil
	}
	transport, err := v2rayxhttp.NewClient(ctx, dialer, serverAddr, options.XHTTPOptions, tlsConfig)
	if err != nil {
		return nil, true, err
	}
	return transport, true, nil
}
