package constant

const (
	V2RayTransportTypeHTTP        = "http"
	V2RayTransportTypeWebsocket   = "ws"
	V2RayTransportTypeQUIC        = "quic"
	V2RayTransportTypeGRPC        = "grpc"
	V2RayTransportTypeHTTPUpgrade = "httpupgrade"
)

// fork-patch: begin xhttp
// V2RayTransportTypeXHTTP is the fork-added XHTTP transport type
// (Xray-compatible, client side). Declared unconditionally so all build
// configurations share one spelling; the transport constructor is only
// reachable when the binary is built with the `with_xhttp` build tag.
// Implementation lands with MUTS-9 in transport/v2rayxhttp.
const V2RayTransportTypeXHTTP = "xhttp"

// fork-patch: end xhttp
