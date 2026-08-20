//go:build with_vless_enc

// Local replacements for the two tiny helpers the reference implementation
// kept in its own packages (Xray: common/crypto.RandBetween,
// common/protocol.HasAESGCMHardwareSupport). Ported from sing-box-lx
// v1.14.0-lx.26 protocol/vless/encryption/lx_support.go (commit 57ece01c).
package encryption

import (
	"crypto/rand"
	"math/big"
	"runtime"

	"golang.org/x/sys/cpu"
)

// Keep in sync with crypto/tls/cipher_suites.go.
//
// Verbatim alignment with Xray-core v26.7.28 common/protocol/headers.go:73-80
// (HasAESGCMHardwareSupport): the client and the server each evaluate this
// formula independently to pick AES-GCM vs ChaCha20-Poly1305 for the wire
// AEAD — any divergence between the two formulas is a silent handshake
// failure, same risk class as padding/ticket field drift. The lx port carried
// three divergences (amd64 missing SSE41/SSSE3, arm64 missing the darwin
// special case, s390x AESCBC vs AESCTR); all three corrected here.
var (
	hasGCMAsmAMD64 = cpu.X86.HasAES && cpu.X86.HasPCLMULQDQ && cpu.X86.HasSSE41 && cpu.X86.HasSSSE3
	hasGCMAsmARM64 = (cpu.ARM64.HasAES && cpu.ARM64.HasPMULL) || (runtime.GOOS == "darwin" && runtime.GOARCH == "arm64")
	hasGCMAsmS390X = cpu.S390X.HasAES && cpu.S390X.HasAESCTR && cpu.S390X.HasGHASH
	hasGCMAsmPPC64 = runtime.GOARCH == "ppc64" || runtime.GOARCH == "ppc64le"

	hasAESGCMHardware = hasGCMAsmAMD64 || hasGCMAsmARM64 || hasGCMAsmS390X || hasGCMAsmPPC64
)

// randBetween returns a uniform random value in [from, to). Used for the
// padding/delay ranges, which are cosmetic on the wire but must not be
// predictable, hence crypto/rand rather than math/rand.
func randBetween(from int64, to int64) int64 {
	if from == to {
		return from
	}
	if from > to {
		from, to = to, from
	}
	bigInt, _ := rand.Int(rand.Reader, big.NewInt(to-from))
	return from + bigInt.Int64()
}
