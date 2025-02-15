import struct

# Define the binary file name
binary_file = 'microservice'  # Replace with your binary file name

# Given data in hex strings
magic_signature_hex = '64 33 6e 30 6c 34 6e 64'
eszip_pos_hex = '00 00 00 00 04 fa ba 30'
metadata_pos_hex = '00 00 00 00 05 00 92 79'
null_pos_hex = '00 00 00 00 05 00 99 1d'
signature_pos_hex = '00 00 00 00 05 01 f4 6e'

# Convert hex strings to bytes
def hex_str_to_bytes(hex_str):
    return bytes.fromhex(hex_str.replace(' ', ''))

magic_signature = hex_str_to_bytes(magic_signature_hex)
eszip_pos_bytes = hex_str_to_bytes(eszip_pos_hex)
metadata_pos_bytes = hex_str_to_bytes(metadata_pos_hex)
null_pos_bytes = hex_str_to_bytes(null_pos_hex)
signature_pos_bytes = hex_str_to_bytes(signature_pos_hex)

# Convert big-endian bytes to integers
def be_bytes_to_int(b):
    return int.from_bytes(b, byteorder='big')

eszip_pos = be_bytes_to_int(eszip_pos_bytes)
metadata_pos = be_bytes_to_int(metadata_pos_bytes)
null_pos = be_bytes_to_int(null_pos_bytes)
signature_pos = be_bytes_to_int(signature_pos_bytes)

# Calculate sizes
eszip_size = metadata_pos - eszip_pos
metadata_size = null_pos - metadata_pos
signature_size = 8  # The magic signature is 8 bytes

print(f"ESZIP position: {eszip_pos}")
print(f"Metadata position: {metadata_pos}")
print(f"Null position: {null_pos}")
print(f"Signature position: {signature_pos}")

print(f"ESZIP size: {eszip_size} bytes")
print(f"Metadata size: {metadata_size} bytes")

# Read the binary file and extract the data
with open(binary_file, 'rb') as f:
    # Extract ESZIP archive
    f.seek(eszip_pos)
    eszip_data = f.read(eszip_size)
    with open('eszip_archive', 'wb') as eszip_file:
        eszip_file.write(eszip_data)
    print("ESZIP archive extracted to 'eszip_archive'.")

    # Extract metadata JSON
    f.seek(metadata_pos)
    metadata_data = f.read(metadata_size)
    with open('metadata.json', 'wb') as metadata_file:
        metadata_file.write(metadata_data)
    print("Metadata extracted to 'metadata.json'.")

    # Extract the magic signature
    f.seek(signature_pos)
    signature_data = f.read(signature_size)
    print(f"Signature data: {signature_data}")

    # Verify the signature
    if signature_data == magic_signature:
        print("Magic signature verified: d3n0l4nd")
    else:
        print("Magic signature does not match.")

    # Optionally, extract the last 40 bytes (footer)
    f.seek(-40, 2)  # 2 means relative to file end
    footer_data = f.read(40)
    with open('binary_footer', 'wb') as footer_file:
        footer_file.write(footer_data)
    print("Binary footer extracted to 'binary_footer'.")
