import base64
from Crypto.PublicKey import RSA
import gmpy2

# Function to decode base64 and convert to integer
def decode_ciphertext(encrypted_message):
    return int.from_bytes(base64.b64decode(encrypted_message), byteorder='big')

# Decode ciphertexts
c1 = decode_ciphertext("B+QWncX2NQpwUWIA+1+PXw7Y9x7eL53vfixIL+N9dRMG9ZKQnOyZARtV+tG1Zfs3z/r0shpW9fhfA9kOVUw/PGx6UpIRbgRXwKd3EZ0MomhxYXeaaxkXbI2lHfCHOhcWHqsGWgaMsSYxykDe9dX8hPtVeZMwXnGKGcGaZLoQ71WNG9e1kQaMB35UozCrNeqjfrvOJu0A5jIEjZkbaiJkhv01Z9SgE9E8ToCoPU2H/6g0j0j+PnDCjCjvaBS7A2AGP+L3twl3XQmrD8GqM38kIcvvdziZoSZwaB13Uzfzli+LBXKBr9RGjwuleQTeInfSBtW9obW1/I4803mqFj7NvQ==")
c2 = decode_ciphertext("ZtMuN9EjxCv+xtsKAhl1ECIi8wIe3CVC7L1HTTBap73V6MZSEjyEf3Ea7HWyW4juyTp2+PdfDBTBmvvLOYSA2Fm3ydGXBuLav98+7nNMcfEw38x6u9NpbsC0d5qgfhks5tSaFQCkgEHH89T+yrkjT6xkJ5kw64Q+jCVWB2uygzueK5RQbmJO9qRDtiOrxN/I+GW1MLjXpiZiPZcDLnKmBbLLq0P1efakIkkRvIHrbeyyZDRvlUu2d9HLXTVKqsqAh9umxjRKTm24wGbAm1jR9iBFEdGhn2PRDPaUMKEsryjbqzGvcyr1OCr3PS8cQBoejCOLia2L/HtwbRJwMXPEqQ==")
c3 = decode_ciphertext("VRvYIQ3rOrAgQpHyInyBfNpqEHUQJEbTM89+l+Os+3BtInbawuVQ/jc/xjuRQwe40wISJPMnh+uDJZiKn2jQZCWK8AqDZN3I7BXcmvSaSLHJI0lOezlEY/7Ps60wr71YXuozxqhQwJ9dgaNSdAv0BaFPvMN1V5+HGQJfc7VqxvdFpIOq1QwVQwvq9a9HGBaUJRv/sCHDt+EHQtXHNyXJ0U1ox9YqmkOBn+nGVKK5D/WI3iMy8qPYu9F3nGYU4gx644wZSbt8Ks0aTJxKs6TYZPez5+sk0Z7qow8tvKvAXInMb4CH2CsYZnfP8EZD2OG7LpBasSOw6QiE+eL1lkxokw==")

# Extract public keys
public_key1 = RSA.import_key('''-----BEGIN RSA PUBLIC KEY-----
MIIBCAKCAQEArqHDiJwi0hddQv1LCxZcPErAT/WRD6PdUoth/ZNqbv+BZq5JIQJg
AEzeEEqh1Wafv/Ks2fMXAMsslW413zm4Lssk5+os/0JLuUje9OKAhKPTacUt4P74
ZfjDIMOIUfcFmtjcM9nQwY7e/SWXzFeSQsrSp+XdYvB3sCDZtthCUTEtW8hKtPe2
H36K+eyQKzDoMcs/BNV+XiSJoeRK1zDqrOYDNy5Jrob/q4vElEd3BlhCAnlyJg0C
wKSnTrDFDccPWJFM+cPjneSsxTyThWZ8Vr2UcZkcO0VJvFedkb0xUpiTdrHyu9l8
JBqG4CEKs+y941WxoXwNa076GMkmmbCZEQIBAw==
-----END RSA PUBLIC KEY-----''')
public_key2 = RSA.import_key('''-----BEGIN RSA PUBLIC KEY-----
MIIBCAKCAQEAt88A0ixTOgd2GpyA4ihONMkmWyEQ89vvCRVtjtcc/lp3SeXZqLpR
tSIrUt0dsBMVIss+aHrquYs7PkN2FmiHCr+uEa5mB2FvxC04iits7mbYjqoZHpHo
cZAntnSUqW4xVZJEqLh/9L/g/U5WhZ4Ta78eJFpDlo2b/vKPQQ/aBNTmCxedpK6k
KW2EEdND0etrKjh2cl4vHz6d7+OmR3X32QTDBXIjjH+nYU09xrCItfx9s27457sA
yXJ6XY1ry4/DxvAY7yRks4Zd7GynI+kUaXuzhf2WZQIKUc/BrkAnhKaZmb9p+j79
Vx5zefStg4JcFQmAMghbJ3XoUYS6DtaukwIBAw==
-----END RSA PUBLIC KEY-----''')
public_key3 = RSA.import_key('''-----BEGIN RSA PUBLIC KEY-----
MIIBCAKCAQEAyKFLqgFkvwrRt4fBSbDXVjiPdR2jo2vkrUfefAzn7YXmgcy8YM06
SWo3jNVy0/MwrMFwymFHSf31OG3WLcY9epGpg0EP4Ha7go66fy6dv47kTzEnbxSk
o4rMTRiapDFaJRWzGbfZRboS/wuQYTsk+itdMwiFMd3jt5xlDs1ULMQfS/xfcbaR
p1BX5DbdmF45CaoTzv+uBI8piGn5eAFG/Yn3L0L09xDZl5Jtw7JlMeZIo8gzOXE5
HL6eBNZ+1bi4x4dwjXHEFNyeFvbKO4EI8nPk7eRMOyZoPFoY9vrFNVlJxgL4bkaP
RxTQVVtkRsC/FEPq6fKxOnG9odDRtDsfWwIBAw==
-----END RSA PUBLIC KEY-----''')

# Get moduli
n1 = public_key1.n
n2 = public_key2.n
n3 = public_key3.n

# Implementing a custom CRT function
def custom_crt(moduli, residues):
    N = 1
    for n in moduli:
        N *= n

    result = 0
    for n_i, a_i in zip(moduli, residues):
        N_i = N // n_i
        # Modular inverse of N_i modulo n_i
        inv = gmpy2.invert(N_i, n_i)
        result += a_i * N_i * inv

    return result % N

# Use the custom CRT function to find x
x = custom_crt([n1, n2, n3], [c1, c2, c3])

# Step 4: Find the cube root of x (since e=3 for Håstad's attack)
m = gmpy2.iroot(x, 3)[0]

# Step 5: Convert the integer m back to bytes
plaintext_bytes = m.to_bytes((m.bit_length() + 7) // 8, byteorder='big')

# Step 6: Strip the PKCS#1 v1.5 padding
if plaintext_bytes.startswith(b'\x00\x02'):
    # Find the first occurrence of \x00 after the padding
    separator_index = plaintext_bytes.find(b'\x00', 2)
    if separator_index != -1:
        plaintext_bytes = plaintext_bytes[separator_index + 1:]

# Convert to string and print the recovered plaintext
plaintext = plaintext_bytes.decode('utf-8', errors='ignore')
print("Recovered plaintext:", plaintext)