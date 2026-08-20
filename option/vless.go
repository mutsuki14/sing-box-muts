package option

type VLESSInboundOptions struct {
	ListenOptions
	Users []VLESSUser `json:"users,omitempty"`
	InboundTLSOptionsContainer
	Multiplex *InboundMultiplexOptions `json:"multiplex,omitempty"`
	Transport *V2RayTransportOptions   `json:"transport,omitempty"`
}

type VLESSUser struct {
	Name string `json:"name"`
	UUID string `json:"uuid"`
	Flow string `json:"flow,omitempty"`
}

type VLESSOutboundOptions struct {
	DialerOptions
	ServerOptions
	UUID    string      `json:"uuid"`
	Flow    string      `json:"flow,omitempty"`
	Network NetworkList `json:"network,omitempty"`
	OutboundTLSOptionsContainer
	Multiplex      *OutboundMultiplexOptions `json:"multiplex,omitempty"`
	Transport      *V2RayTransportOptions    `json:"transport,omitempty"`
	PacketEncoding *string                   `json:"packet_encoding,omitempty"`
	// fork-patch: begin vless-enc
	// Encryption enables the VLESS post-quantum encryption layer
	// (mlkem768x25519plus), which lives inside VLESS beneath the transport
	// and independent of TLS. Spec string:
	// "mlkem768x25519plus.<native|xorpub|random>.<0rtt|1rtt>[.<padding>].<key>…".
	// Empty or "none" leaves the layer off. The layer itself is only compiled
	// in under the `with_vless_enc` build tag; without it a configured value
	// is rejected at outbound construction (MUTS-10).
	Encryption string `json:"encryption,omitempty"`
	// fork-patch: end vless-enc
}
