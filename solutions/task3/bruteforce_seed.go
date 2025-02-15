package main

import (
	"encoding/binary"
	"fmt"
	"math/rand"
)

// getChunks splits a username into 4-byte chunks for XOR operations
func getChunks(username string) []uint32 {
	usernameBytes := []byte(username)
	padding := (4 - len(usernameBytes)%4) % 4
	usernameBytes = append(usernameBytes, make([]byte, padding)...)

	var chunks []uint32
	for i := 0; i < len(usernameBytes); i += 4 {
		chunks = append(chunks, binary.LittleEndian.Uint32(usernameBytes[i:i+4]))
	}
	return chunks
}

// performXOR performs XOR on the initial uVar2 with chunks from the username
func performXOR(uVar2 uint32, chunks []uint32) uint32 {
	for _, chunk := range chunks {
		uVar2 ^= chunk
	}
	return uVar2
}

// simulateAuthBypass checks if the current random value XOR'd with the username meets the bypass condition
func simulateAuthBypass(username string, uVar2Initial uint32, targetUVar2 uint32) (bool, uint32) {
	usernameChunks := getChunks(username)
	finalUVar2 := performXOR(uVar2Initial, usernameChunks)

	// Return true if the bypass condition is met
	if finalUVar2 == targetUVar2 {
		return true, finalUVar2
	}
	return false, finalUVar2
}

func main() {
	// Fixed initial random seed from the server code
	seed := int64(0x76546CC2CA2D7)
	rand.Seed(seed)
	rand.Int63()

	// Bypass target value
	targetUVar2 := uint32(0x8A700A02)

	// Iterate over seed count (1,000,000,000,000,000 iterations)
	maxIterations := 1000000000000000

	username := "jasper_05376"

	fmt.Println("Starting bypass detection...")

	showNext := 0

	for count := 1; count <= maxIterations; count++ {
		// Get the current random value (uVar2Initial is the lower 32-bits of currentRand)
		currentRand := rand.Int63()
		uVar2Initial := uint32(currentRand & 0xFFFFFFFF)

		bypass, finalUVar2 := simulateAuthBypass(username, uVar2Initial, targetUVar2)

		if bypass || count < 10 || showNext == 1 {
			// check the first 10 initial value to compare if the simulation matches the program's behavior
			// Display the bypass information
			fmt.Printf("\nBypass detected!\n")
			fmt.Printf("Username: %s\n", username)
			fmt.Printf("Seed Count: %d\n", count)
			fmt.Printf("Initial uVar2: 0x%x\n", uVar2Initial)
			fmt.Printf("Final uVar2: 0x%x (Matches Bypass Value)\n", finalUVar2)
			fmt.Printf("CurrentRand: %d\n\n", currentRand)
			if count > 10 {
				showNext++
			}
		}

		// Show progress
		if count%100000000 == 0 {
			fmt.Printf("Processed %d seed iterations...\n", count)
		}
	}

	fmt.Println("Bypass detection completed.")
}
