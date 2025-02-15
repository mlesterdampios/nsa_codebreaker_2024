package main

import (
	"bytes"
	"encoding/base32"
	"crypto/rand"
	"crypto/subtle"
	"encoding/binary"
	"errors"
	"fmt"
	"encoding/hex"
	"golang.org/x/crypto/blake2s"
	"golang.org/x/crypto/chacha20poly1305"
	"golang.org/x/crypto/curve25519"
	"golang.org/x/crypto/hkdf"
	"hash"
	"io"
	"math"
	"os/exec"
	"regexp"
	"strings"
)

// Constants provided in the challenge
var initiatorPublicKey = [32]byte{
	0xB6, 0xB0, 0x1E, 0x07, 0xB1, 
	0xD4, 0xB1, 0x1E, 0x71, 0xA6, 
	0x37, 0x6C, 0xE5, 0xEA, 0x49, 
	0x55, 0xFF, 0x70, 0x3D, 0xF0, 
	0xFE, 0x9E, 0xC4, 0xB7, 0x3E, 
	0xDB, 0xB4, 0xA0, 0xE2, 0x64, 
	0x46, 0x09,
}

var responderPrivateKey = [32]byte{
	0xD3, 0xDA, 0x9E, 0x41, 0xB9, 
	0x75, 0x55, 0x35, 0xAE, 0x62, 
	0x12, 0x37, 0xEC, 0x7C, 0x2B, 
	0x77, 0x0D, 0xA0, 0x4A, 0x83, 
	0x4A, 0xE6, 0x59, 0xF5, 0x80, 
	0xB0, 0x99, 0x3B, 0x2C, 0xB1, 
	0x69, 0xDD,
}

// Small order point not in forbiddenCurveValues
var smallOrderPublicKey = [32]byte{
	0x00, 0x00, 0x00, 0x00, 0x00, // bytes 0-4
	0x00, 0x00, 0x00, 0x00, 0x00, // bytes 5-9
	0x00, 0x00, 0x00, 0x00, 0x00, // bytes 10-14
	0x00, 0x00, 0x00, 0x00, 0x00, // bytes 15-19
	0x00, 0x00, 0x00, 0x00, 0x00, // bytes 20-24
	0x00, 0x00, 0x00, 0x00, 0x00, // bytes 25-29
	0x00, 0x80, // bytes 30-31
}

/* ---------------------------------------------------------------- *
 * TYPES                                                            *
 * ---------------------------------------------------------------- */

type keypair struct {
	public_key  [32]byte
	private_key [32]byte
}

type messagebuffer struct {
	ne         [32]byte
	ns         []byte
	ciphertext []byte
}

type cipherstate struct {
	k [32]byte
	n uint64
}

type symmetricstate struct {
	cs cipherstate
	ck [32]byte
	h  [32]byte
}

type handshakestate struct {
	ss  symmetricstate
	s   keypair
	e   keypair
	rs  [32]byte
	re  [32]byte
	psk [32]byte
}

type noisesession struct {
	hs  handshakestate
	h   [32]byte
	cs1 cipherstate
	cs2 cipherstate
	mc  uint64
	i   bool
}

/* ---------------------------------------------------------------- *
 * CONSTANTS                                                        *
 * ---------------------------------------------------------------- */

var emptyKey = [32]byte{
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00,
}

var minNonce = uint64(0)

/* ---------------------------------------------------------------- *
 * UTILITY FUNCTIONS                                                *
 * ---------------------------------------------------------------- */

func getPublicKey(kp *keypair) [32]byte {
	return kp.public_key
}

func isEmptyKey(k [32]byte) bool {
	return subtle.ConstantTimeCompare(k[:], emptyKey[:]) == 1
}

func validatePublicKey(k []byte) bool {
	forbiddenCurveValues := [12][]byte{
		{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
		{1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
		{224, 235, 122, 124, 59, 65, 184, 174, 22, 86, 227, 250, 241, 159, 196, 106, 218, 9, 141, 235, 156, 50, 177, 253, 134, 98, 5, 22, 95, 73, 184, 0},
		{95, 156, 149, 188, 163, 80, 140, 36, 177, 208, 177, 85, 156, 131, 239, 91, 4, 68, 92, 196, 88, 28, 142, 134, 216, 34, 78, 221, 208, 159, 17, 87},
		{236, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 127},
		{237, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 127},
		{238, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 127},
		{205, 235, 122, 124, 59, 65, 184, 174, 22, 86, 227, 250, 241, 159, 196, 106, 218, 9, 141, 235, 156, 50, 177, 253, 134, 98, 5, 22, 95, 73, 184, 128},
		{76, 156, 149, 188, 163, 80, 140, 36, 177, 208, 177, 85, 156, 131, 239, 91, 4, 68, 92, 196, 88, 28, 142, 134, 216, 34, 78, 221, 208, 159, 17, 215},
		{217, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255},
		{218, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255},
		{219, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 25},
	}

	for _, testValue := range forbiddenCurveValues {
		if subtle.ConstantTimeCompare(k[:], testValue[:]) == 1 {
			panic("Invalid public key")
		}
	}
	return true
}
/* ---------------------------------------------------------------- *
 * PRIMITIVES                                                       *
 * ---------------------------------------------------------------- */

func incrementNonce(n uint64) uint64 {
	return n + 1
}

func dh(private_key [32]byte, public_key [32]byte) [32]byte {
	var ss [32]byte
	curve25519.ScalarMult(&ss, &private_key, &public_key)
	return ss
}

func generateKeypair() keypair {
	var public_key [32]byte
	var private_key [32]byte
	_, _ = rand.Read(private_key[:])
	curve25519.ScalarBaseMult(&public_key, &private_key)
	if validatePublicKey(public_key[:]) {
		return keypair{public_key, private_key}
	}
	return generateKeypair()
}

func generatePublicKey(private_key [32]byte) [32]byte {
	var public_key [32]byte
	curve25519.ScalarBaseMult(&public_key, &private_key)
	return public_key
}

func encrypt(k [32]byte, n uint64, ad []byte, plaintext []byte) []byte {
	var nonce [12]byte
	var ciphertext []byte
	enc, _ := chacha20poly1305.New(k[:])
	binary.LittleEndian.PutUint64(nonce[4:], n)
	ciphertext = enc.Seal(nil, nonce[:], plaintext, ad)
	return ciphertext
}

func decrypt(k [32]byte, n uint64, ad []byte, ciphertext []byte) (bool, []byte, []byte) {
	var nonce [12]byte
	var plaintext []byte
	enc, err := chacha20poly1305.New(k[:])
	binary.LittleEndian.PutUint64(nonce[4:], n)
	plaintext, err = enc.Open(nil, nonce[:], ciphertext, ad)
	return (err == nil), ad, plaintext
}

func getHash(a []byte, b []byte) [32]byte {
	return blake2s.Sum256(append(a, b...))
}

func hashProtocolName(protocolName []byte) [32]byte {
	var h [32]byte
	if len(protocolName) <= 32 {
		copy(h[:], protocolName)
	} else {
		h = getHash(protocolName, []byte{})
	}
	return h
}

func blake2HkdfInterface() hash.Hash {
	h, _ := blake2s.New256([]byte{})
	return h
}

func getHkdf(ck [32]byte, ikm []byte) ([32]byte, [32]byte, [32]byte) {
	var k1 [32]byte
	var k2 [32]byte
	var k3 [32]byte
	output := hkdf.New(blake2HkdfInterface, ikm[:], ck[:], []byte{})
	io.ReadFull(output, k1[:])
	io.ReadFull(output, k2[:])
	io.ReadFull(output, k3[:])
	return k1, k2, k3
}

/* ---------------------------------------------------------------- *
 * STATE MANAGEMENT                                                 *
 * ---------------------------------------------------------------- */

/* CipherState */
func initializeKey(k [32]byte) cipherstate {
	return cipherstate{k, minNonce}
}

func hasKey(cs *cipherstate) bool {
	return !isEmptyKey(cs.k)
}

func setNonce(cs *cipherstate, newNonce uint64) *cipherstate {
	cs.n = newNonce
	return cs
}

func encryptWithAd(cs *cipherstate, ad []byte, plaintext []byte) (*cipherstate, []byte, error) {
	var err error
	if cs.n == math.MaxUint64-1 {
		err = errors.New("encryptWithAd: maximum nonce size reached")
		return cs, []byte{}, err
	}
	e := encrypt(cs.k, cs.n, ad, plaintext)
	cs = setNonce(cs, incrementNonce(cs.n))
	return cs, e, err
}

func decryptWithAd(cs *cipherstate, ad []byte, ciphertext []byte) (*cipherstate, []byte, bool, error) {
	var err error
	if cs.n == math.MaxUint64-1 {
		err = errors.New("decryptWithAd: maximum nonce size reached")
		return cs, []byte{}, false, err
	}
	valid, ad, plaintext := decrypt(cs.k, cs.n, ad, ciphertext)
	if valid {
		cs = setNonce(cs, incrementNonce(cs.n))
	}
	return cs, plaintext, valid, err
}

func reKey(cs *cipherstate) *cipherstate {
	e := encrypt(cs.k, math.MaxUint64, []byte{}, emptyKey[:])
	copy(cs.k[:], e)
	return cs
}

/* SymmetricState */

func initializeSymmetric(protocolName []byte) symmetricstate {
	h := hashProtocolName(protocolName)
	ck := h
	cs := initializeKey(emptyKey)
	return symmetricstate{cs, ck, h}
}

func mixKey(ss *symmetricstate, ikm [32]byte) *symmetricstate {
	ck, tempK, _ := getHkdf(ss.ck, ikm[:])
	ss.cs = initializeKey(tempK)
	ss.ck = ck
	return ss
}

func mixHash(ss *symmetricstate, data []byte) *symmetricstate {
	ss.h = getHash(ss.h[:], data)
	return ss
}

func mixKeyAndHash(ss *symmetricstate, ikm [32]byte) *symmetricstate {
	var tempH [32]byte
	var tempK [32]byte
	ss.ck, tempH, tempK = getHkdf(ss.ck, ikm[:])
	ss = mixHash(ss, tempH[:])
	ss.cs = initializeKey(tempK)
	return ss
}

func getHandshakeHash(ss *symmetricstate) [32]byte {
	return ss.h
}

func encryptAndHash(ss *symmetricstate, plaintext []byte) (*symmetricstate, []byte, error) {
	var ciphertext []byte
	var err error
	if hasKey(&ss.cs) {
		_, ciphertext, err = encryptWithAd(&ss.cs, ss.h[:], plaintext)
		if err != nil {
			return ss, []byte{}, err
		}
	} else {
		ciphertext = plaintext
	}
	ss = mixHash(ss, ciphertext)
	return ss, ciphertext, err
}

func decryptAndHash(ss *symmetricstate, ciphertext []byte) (*symmetricstate, []byte, bool, error) {
	var plaintext []byte
	var valid bool
	var err error
	if hasKey(&ss.cs) {
		_, plaintext, valid, err = decryptWithAd(&ss.cs, ss.h[:], ciphertext)
		if err != nil {
			return ss, []byte{}, false, err
		}
	} else {
		plaintext, valid = ciphertext, true
	}
	ss = mixHash(ss, ciphertext)
	return ss, plaintext, valid, err
}

func split(ss *symmetricstate) (cipherstate, cipherstate) {
	tempK1, tempK2, _ := getHkdf(ss.ck, []byte{})
	cs1 := initializeKey(tempK1)
	cs2 := initializeKey(tempK2)
	return cs1, cs2
}

/* HandshakeState */

func initializeInitiator(prologue []byte, s keypair, rs [32]byte, psk [32]byte) handshakestate {
	var ss symmetricstate
	var e keypair
	var re [32]byte
	name := []byte("Noise_K_25519_ChaChaPoly_BLAKE2s")
	ss = initializeSymmetric(name)
	mixHash(&ss, prologue)
	mixHash(&ss, s.public_key[:])
	mixHash(&ss, rs[:])
	return handshakestate{ss, s, e, rs, re, psk}
}

func initializeResponder(prologue []byte, s keypair, rs [32]byte, psk [32]byte) handshakestate {
	var ss symmetricstate
	var e keypair
	var re [32]byte
	name := []byte("Noise_K_25519_ChaChaPoly_BLAKE2s")
	ss = initializeSymmetric(name)
	mixHash(&ss, prologue)
	mixHash(&ss, rs[:])
	mixHash(&ss, s.public_key[:])
	return handshakestate{ss, s, e, rs, re, psk}
}

func writeMessageA(hs *handshakestate, payload []byte) ([32]byte, messagebuffer, cipherstate, cipherstate, error) {
	var err error
	var messageBuffer messagebuffer
	ne, ns, ciphertext := emptyKey, []byte{}, []byte{}
	hs.e = generateKeypair()
	ne = hs.e.public_key
	mixHash(&hs.ss, ne[:])
	/* No PSK, so skipping mixKey */
	mixKey(&hs.ss, dh(hs.e.private_key, hs.rs))
	mixKey(&hs.ss, dh(hs.s.private_key, hs.rs))
	_, ciphertext, err = encryptAndHash(&hs.ss, payload)
	if err != nil {
		cs1, cs2 := split(&hs.ss)
		return hs.ss.h, messageBuffer, cs1, cs2, err
	}
	messageBuffer = messagebuffer{ne, ns, ciphertext}
	cs1, cs2 := split(&hs.ss)
	return hs.ss.h, messageBuffer, cs1, cs2, err
}

func writeMessageRegular(cs *cipherstate, payload []byte) (*cipherstate, messagebuffer, error) {
	var err error
	var messageBuffer messagebuffer
	ne, ns, ciphertext := emptyKey, []byte{}, []byte{}
	cs, ciphertext, err = encryptWithAd(cs, []byte{}, payload)
	if err != nil {
		return cs, messageBuffer, err
	}
	messageBuffer = messagebuffer{ne, ns, ciphertext}
	return cs, messageBuffer, err
}

func readMessageA(hs *handshakestate, message *messagebuffer) ([32]byte, []byte, bool, cipherstate, cipherstate, error) {
	var err error
	var plaintext []byte
	var valid2 bool = false
	var valid1 bool = true
	if validatePublicKey(message.ne[:]) {
		hs.re = message.ne
	}
	mixHash(&hs.ss, hs.re[:])

	/* No PSK, so skipping mixKey */
	dh1 := dh(hs.s.private_key, hs.re)
	mixKey(&hs.ss, dh1)

	hsReHex := hex.EncodeToString(hs.re[:])
	fmt.Println("[readMessageA] hs.re (hex):", hsReHex, "\n")

	dh1Hex := hex.EncodeToString(dh1[:])
	fmt.Println("[readMessageA] dh1 (hex):", dh1Hex, "\n")

	dh2 := dh(hs.s.private_key, initiatorPublicKey)

	mixKey(&hs.ss, dh2) // hardcoded in the binary

	hsSPrivate_keyHex := hex.EncodeToString(hs.s.private_key[:])
	fmt.Println("[readMessageA] hs.s.private_key (hex):", hsSPrivate_keyHex, "\n")

	initiatorPublicKeyHex := hex.EncodeToString(initiatorPublicKey[:])
	fmt.Println("[readMessageA] initiatorPublicKey (hex):", initiatorPublicKeyHex, "\n")

	dh2Hex := hex.EncodeToString(dh2[:])
	fmt.Println("[readMessageA] dh2 (hex):", dh2Hex, "\n")

	_, plaintext, valid2, err = decryptAndHash(&hs.ss, message.ciphertext)
	cs1, cs2 := split(&hs.ss)
	return hs.ss.h, plaintext, (valid1 && valid2), cs1, cs2, err
}

func readMessageRegular(cs *cipherstate, message *messagebuffer) (*cipherstate, []byte, bool, error) {
	var err error
	var plaintext []byte
	var valid2 bool = false
	/* No encrypted keys */
	_, plaintext, valid2, err = decryptWithAd(cs, []byte{}, message.ciphertext)
	return cs, plaintext, valid2, err
}

/* ---------------------------------------------------------------- *
 * PROCESSES                                                        *
 * ---------------------------------------------------------------- */

func InitSession(initiator bool, prologue []byte, s keypair, rs [32]byte) noisesession {
	var session noisesession
	psk := emptyKey
	if initiator {
		session.hs = initializeInitiator(prologue, s, rs, psk)
	} else {
		session.hs = initializeResponder(prologue, s, rs, psk)
	}
	session.i = initiator
	session.mc = 0
	return session
}

func SendMessage(session *noisesession, message []byte) (*noisesession, messagebuffer, error) {
	var err error
	var messageBuffer messagebuffer
	if session.mc == 0 {
		session.h, messageBuffer, session.cs1, _, err = writeMessageA(&session.hs, message)
		session.hs = handshakestate{}
	}
	if session.mc > 0 {
		if session.i {
			_, messageBuffer, err = writeMessageRegular(&session.cs1, message)
		} else {
			_, messageBuffer, err = writeMessageRegular(&session.cs1, message)
		}
	}
	session.mc = session.mc + 1
	return session, messageBuffer, err
}

func RecvMessage(session *noisesession, message *messagebuffer) (*noisesession, []byte, bool, error) {
	var err error
	var plaintext []byte
	var valid bool
	if session.mc == 0 {
		session.h, plaintext, valid, session.cs1, _, err = readMessageA(&session.hs, message)
		session.hs = handshakestate{}
	}
	if session.mc > 0 {
		if session.i {
			_, plaintext, valid, err = readMessageRegular(&session.cs1, message)
		} else {
			_, plaintext, valid, err = readMessageRegular(&session.cs1, message)
		}
	}
	session.mc = session.mc + 1
	return session, plaintext, valid, err
}

/* ---------------------------------------------------------------- *
 * EXPLOIT IMPLEMENTATION                                           *
 * ---------------------------------------------------------------- */

func main() {
	// Known prologue (assuming empty for this example)
	prologue := []byte{}

	// Responder's public key (computed from private key)
	var responderPublicKey [32]byte
	curve25519.ScalarBaseMult(&responderPublicKey, &responderPrivateKey)
	responderPrivateKeyHex := hex.EncodeToString(responderPrivateKey[:])
	fmt.Println("responderPrivateKey (hex):", responderPrivateKeyHex, "\n")
	responderPublicKeyHex := hex.EncodeToString(responderPublicKey[:])
	fmt.Println("responderPublicKey (hex):", responderPublicKeyHex, "\n")

	initiatorPublicKeyHex := hex.EncodeToString(initiatorPublicKey[:])
	fmt.Println("initiatorPublicKey (hex):", initiatorPublicKeyHex, "\n")

	// Initialize symmetric state as responder
	name := []byte("Noise_K_25519_ChaChaPoly_BLAKE2s")
	ss := initializeSymmetric(name)
	mixHash(&ss, prologue)
	mixHash(&ss, initiatorPublicKey[:])
	mixHash(&ss, responderPublicKey[:])

	// Simulate responder's processing of the message

	// hs.re is the small order point we send
	hsRe := smallOrderPublicKey

	hsReHex := hex.EncodeToString(hsRe[:])
	fmt.Println("hsRe (hex):", hsReHex, "\n")

	mixHash(&ss, hsRe[:])

	// Compute dh(hs.s.privateKey, hs.re)
	dh1 := dh(responderPrivateKey, hsRe)

	dh1Hex := hex.EncodeToString(dh1[:])
	fmt.Println("dh1 (hex):", dh1Hex, "\n")

	// MixKey with dh1
	mixKey(&ss, dh1)

	// Compute dh(hs.s.privateKey, hs.rs)
	dh2 := dh(responderPrivateKey, initiatorPublicKey)

	responderPrivateKeyHex2 := hex.EncodeToString(responderPrivateKey[:])
	fmt.Println("responderPrivateKey (hex):", responderPrivateKeyHex2, "\n")

	initiatorPublicKeyHex2 := hex.EncodeToString(initiatorPublicKey[:])
	fmt.Println("initiatorPublicKey (hex):", initiatorPublicKeyHex2, "\n")

	dh2Hex := hex.EncodeToString(dh2[:])
	fmt.Println("dh2 (hex):", dh2Hex, "\n")

	// MixKey with dh2
	mixKey(&ss, dh2)

	// At this point, ss.ck and ss.cs.k contain the chain key and cipher key the responder will use

	// Now, as the attacker (initiator), we can compute the same keys

	// Initialize symmetric state as initiator
	initSS := initializeSymmetric(name)
	mixHash(&initSS, prologue)
	mixHash(&initSS, initiatorPublicKey[:])
	mixHash(&initSS, responderPublicKey[:])

	// We use the same hs.e.publicKey (small order point)
	hsEPublicKey := smallOrderPublicKey
	mixHash(&initSS, hsEPublicKey[:])

	// Since we don't have the initiator's private key, but we can set it to zero
	var zeroPrivateKey [32]byte

	// Compute dh(hs.e.privateKey, hs.rs) with zero private key
	dh1Initiator := dh(zeroPrivateKey, responderPublicKey)
	mixKey(&initSS, dh1Initiator)

	// Compute dh(hs.s.privateKey, hs.rs) with zero private key
	dh2Initiator := dh(zeroPrivateKey, responderPublicKey)
	mixKey(&initSS, dh2Initiator)

	// Now, initSS.ck and initSS.cs.k are the keys the initiator would have
	// However, since we used zero private keys, the dh outputs are zeros
	// But we know the responder's keys from earlier, so we can use those

	// For the exploit, we'll use the responder's ss.ck and ss.cs.k to encrypt the payload
	payload := []byte("Secret message from initiator")

	// Encrypt the payload using the responder's cipher key and handshake hash
	ciphertext := encrypt(ss.cs.k, ss.cs.n, ss.h[:], payload)
	ss.cs.n = incrementNonce(ss.cs.n)

	// Prepare the message buffer to send to the responder
	message := messagebuffer{
		ne:         smallOrderPublicKey, // Our crafted ephemeral public key
		ns:         []byte{},            // No static key sent
		ciphertext: ciphertext,
	}

	// The responder will process the message using their state
	// For demonstration, we can show that the responder can decrypt the message

	// Responder decrypts the ciphertext
	valid, _, decryptedPayload := decrypt(ss.cs.k, ss.cs.n-1, ss.h[:], message.ciphertext)
	if valid {
		fmt.Println("Responder decrypted the message successfully:")
		fmt.Println(string(decryptedPayload))
	} else {
		fmt.Println("Responder failed to decrypt the message.")
	}

	responderSession := InitSession(false, prologue, keypair{responderPublicKey, responderPrivateKey}, initiatorPublicKey)

	_, plaintext, valid, err := RecvMessage(&responderSession, &message)
	if err != nil {
		panic(err)
	}
	if !valid {
		panic("Decryption failed!")
	}

	// Output the decrypted message
	fmt.Printf("Responder decrypted message: %s\n", string(plaintext))

	encode_msg(message)
}

// ProcessAndDig processes the input string according to the specified rules,
// ensures the final domain matches the given regex, and performs a DNS A record
// lookup on port 1053 using the dig command.
// It returns the final domain and the output of the dig command.
func ProcessAndDig(input string) (string, string, error) {
	// Step 1: Replace all "=" with "z"
	processedInput := strings.ReplaceAll(input, "=", "z")

	// Step 2: Define constants
	const (
		partLength    = 62
		requiredParts = 3
	)

	// Step 3: Truncate input to fit into the required number of parts
	maxLength := partLength * requiredParts
	if len(processedInput) > maxLength {
		processedInput = processedInput[:maxLength]
	}

	// Step 4: Split the string into requiredParts parts of partLength each
	parts := make([]string, requiredParts)
	for i := 0; i < requiredParts; i++ {
		start := i * partLength
		end := start + partLength
		if start >= len(processedInput) {
			// If no more characters, pad entirely with 'x's
			parts[i] = strings.Repeat("x", partLength)
			continue
		}
		if end > len(processedInput) {
			// If the last part is shorter, pad with 'x's
			part := processedInput[start:]
			paddingLength := partLength - len(part)
			part += strings.Repeat("x", paddingLength)
			parts[i] = part
		} else {
			parts[i] = processedInput[start:end]
		}
	}

	// Step 5: Prefix each part with "x" and append "."
	for i, part := range parts {
		parts[i] = "x" + part + "."
	}

	// Step 6: Concatenate all parts and append the final domain suffix with a trailing dot
	finalDomain := strings.Join(parts, "") + "net-jl7s7rd2.example.com."

	// Step 7: Validate the finalDomain against the regex
	regexPattern := `^x[^.]{62}\.x[^.]{62}\.x[^.]{62}\.net-jl7s7rd2\.example\.com\.$`
	matched, err := regexp.MatchString(regexPattern, finalDomain)
	if err != nil {
		return "", "", fmt.Errorf("regex match error: %v", err)
	}
	if !matched {
		return "", "", fmt.Errorf("final domain does not match the required pattern")
	}

	// Step 8: Prepare the dig command
	// Remove the trailing dot for the dig command if necessary
	digDomain := strings.TrimSuffix(finalDomain, ".")
	digCmd := exec.Command("dig", "@localhost", "-p", "1053", "+tries=0", "+retry=0", digDomain, "A")

	// Execute the dig command and capture the output
	var outBuffer bytes.Buffer
	var errBuffer bytes.Buffer
	digCmd.Stdout = &outBuffer
	digCmd.Stderr = &errBuffer

	err = digCmd.Run()
	if err != nil {
		return finalDomain, "", fmt.Errorf("dig command failed: %v, stderr: %s", err, errBuffer.String())
	}

	// Return the final domain and the output of the dig command
	return finalDomain, outBuffer.String(), nil
}

func encode_msg(messageBuffer messagebuffer) () {
    var HexEncoding = base32.NewEncoding("0123456789ABCDEFGHIJKLMNOPQRSTUV")

	var concatenated []byte
    concatenated = append(concatenated, messageBuffer.ne[:]...)
    concatenated = append(concatenated, messageBuffer.ns...)
    concatenated = append(concatenated, messageBuffer.ciphertext...)
	fmt.Printf("concatenated: %x\n", concatenated)


    encodedData := HexEncoding.EncodeToString([]byte(concatenated))
    fmt.Println("Encoded Data:", (encodedData))

	// Call the ProcessAndDig function
	finalDomain, digOutput, err := ProcessAndDig(encodedData)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	// Print the final domain
	fmt.Println("Final Domain:", finalDomain)

	// Print the dig command output
	fmt.Println("\nDig Command Output:")
	fmt.Println(digOutput)
}