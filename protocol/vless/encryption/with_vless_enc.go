//go:build with_vless_enc

package encryption

// Real installation (MUTS-10): parse the spec string and initialize the
// mlkem768x25519plus client layer ported from sing-box-lx. A malformed spec
// fails here, at config time, with an error naming the offending segment —
// never later as a silent handshake failure.
func init() {
	NewInstance = func(spec string) (Instance, error) {
		config, err := parseClientEncryption(spec)
		if err != nil {
			return nil, err
		}
		instance := &ClientInstance{}
		if err := instance.Init(config.keys, config.xorMode, config.seconds, config.padding); err != nil {
			return nil, err
		}
		return instance, nil
	}
}
