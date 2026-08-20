//go:build !with_vless_enc

package encryption

// Without the `with_vless_enc` build tag the encryption layer is absent:
// Layer stays nil and the VLESS outbound keeps exact upstream behavior.
// This file intentionally contains no code; it exists so the negative
// configuration is visible in the package layout.
