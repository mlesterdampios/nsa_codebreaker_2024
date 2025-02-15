from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib
import time

# Provided data
aws_encrypted = b'\x7c\x30\x03\x7e\xec\x00\xb2\xe1\xf4\x09\xea\x92\x27\x2d\x1e\x80\x71\x89\x2b\xb9\xa1\x4e\x39\xf2\x05\x7b\xda\xa6\x83\x0b\x2d\xbc\xff\xdc'
aws_plaintext = "r2s^PKT=lW2L(wmG06"
usb_encrypted = b'\x7c\x30\x03\x7e\xec\x00\xb2\xe1\xf4\x09\xea\x92\x27\x2d\x1e\x80\x38\xc8\x01\xdb\xa5\x43\x5c\xe2\x2c\x76\x8b\xc0\xdd\x54\x2e\xac\x1b\xbb'


# Extract IV (first 16 bytes)
iv = usb_encrypted[:16]

# Extract ciphertexts (excluding IV)
usb_ciphertext = usb_encrypted[16:]
aws_ciphertext = aws_encrypted[16:]

# Convert plaintext to bytes
aws_plaintext_bytes = aws_plaintext.encode()

# Function to derive the keystream and decrypt usb_ciphertext until non-UTF-8 encountered
def brute_force_until_invalid_utf8(aws_plaintext_bytes, aws_ciphertext, usb_ciphertext):
    possible_plaintexts = []
    # Brute-force until a non-UTF-8 character is encountered
    for length in range(1, len(aws_plaintext_bytes) + 1):
        # Derive the partial keystream for the current length
        keystream = bytes(c ^ p for c, p in zip(aws_ciphertext[:length], aws_plaintext_bytes[:length]))

        # Attempt to recover the usb plaintext using the partial keystream
        usb_plaintext = bytes(c ^ k for c, k in zip(usb_ciphertext[:length], keystream))
        
        # Attempt to recover aws plaintext to validate against the original plaintext
        aws_recovered = bytes(c ^ k for c, k in zip(aws_ciphertext[:length], keystream))
        
        try:
            usb_plaintext_string = usb_plaintext.decode('utf-8')
            aws_recovered_string = aws_recovered.decode('utf-8')
            
            # Check if aws_recovered matches aws_plaintext for validation
            if aws_recovered_string == aws_plaintext[:length]:
                possible_plaintexts.append((length, usb_plaintext_string, aws_recovered_string))
        except UnicodeDecodeError:
            # Stop if non-UTF-8 character is encountered
            break
    
    return possible_plaintexts

# Perform brute-force decryption
decrypted_plaintexts = brute_force_until_invalid_utf8(aws_plaintext_bytes, aws_ciphertext, usb_ciphertext)

# Output all possible plaintexts to a file
with open('usb_plaintext.txt', 'w') as f:
    for length, usb_plaintext, aws_recovered in decrypted_plaintexts:
        f.write(f"{usb_plaintext}\n")