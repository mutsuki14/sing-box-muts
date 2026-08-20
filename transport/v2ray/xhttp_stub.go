//go:build !with_xhttp

package v2ray

import (
	"context"

	"github.com/sagernet/sing-box/adapter"
	"github.com/sagernet/sing-box/common/tls"
	"github.com/sagernet/sing-box/option"
	M "github.com/sagernet/sing/common/metadata"
	N "github.com/sagernet/sing/common/network"
)

// newXHTTPClientTransport without the `with_xhttp` build tag never handles
// the dispatch, so NewClientTransport falls through to the upstream
// unknown-type error and the binary behaves exactly like upstream.
func newXHTTPClientTransport(ctx context.Context, dialer N.Dialer, serverAddr M.Socksaddr, options option.V2RayTransportOptions, tlsConfig tls.Config) (adapter.V2RayClientTransport, bool, error) {
	return nil, false, nil
}
