//go:build !with_xhttp

package option

import (
	E "github.com/sagernet/sing/common/exceptions"
)

// V2RayXHTTPOptions is the tag-off placeholder for the XHTTP transport schema
// (MUTS-9). The full schema lives in v2ray_xhttp.go behind `with_xhttp`; this
// empty struct only exists so the fork-patch field on _V2RayTransportOptions
// compiles in both build flavors. No xhttp config can ever be decoded into it:
// the hooks below reject "xhttp" with the exact upstream unknown-type error
// before any field is filled, keeping tag-off parsing byte-identical to
// upstream (fork-maintenance §1.4).
type V2RayXHTTPOptions struct{}

// xhttpMarshalOptions without `with_xhttp` behaves exactly like upstream: a
// transport of type "xhttp" is unknown and rejected at the option layer.
func xhttpMarshalOptions(o V2RayTransportOptions) (any, error) {
	return nil, E.New("unknown transport type: " + o.Type)
}

// xhttpUnmarshalTarget without `with_xhttp` rejects with the exact upstream
// error, so the decode result matches upstream byte for byte.
func xhttpUnmarshalTarget(o *V2RayTransportOptions) (any, error) {
	return nil, E.New("unknown transport type: " + o.Type)
}
