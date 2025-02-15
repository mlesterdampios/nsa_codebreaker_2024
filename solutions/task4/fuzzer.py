import httpx
import json
import os
import argparse
import tempfile
from urllib.parse import quote
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Function to load .p12 file
def load_p12_certificate(p12_path, p12_password):
    with open(p12_path, "rb") as p12_file:
        p12_data = p12_file.read()
    private_key, certificate, additional_certs = load_key_and_certificates(
        p12_data, 
        p12_password.encode(), 
        default_backend()
    )
    return private_key, certificate

# Function to create a filename-safe version of a query string
def sanitize_filename(query, max_length=255):
    # Replace spaces with underscores and remove invalid filename characters
    sanitized = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in query)
    # Truncate if too long, and leave space for file extension
    if len(sanitized) > max_length - 5:  # Reserving space for ".json"
        sanitized = sanitized[:max_length - 5]
    return sanitized

# Function to make a request and save response as JSON
def make_request_and_save(query, client, save_location):
    url = f"https://34.195.208.56/?q={quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Te": "trailers"
    }
    
    response = client.get(url, headers=headers)
    
    body = response.json()
    output_data = {
        "q": query,
        "body": body
    }
    
    # Sanitize filename and save as JSON
    filename = sanitize_filename(query) + ".json"
    full_path = os.path.join(save_location, filename)
    with open(full_path, "w") as f:
        json.dump(output_data, f, indent=4)
    print(f"Saved response to {full_path}")

# Main function to read queries and perform requests
def main(p12_path, p12_password, queries_file, save_location):
    private_key, certificate = load_p12_certificate(p12_path, p12_password)
    
    # Serialize private key and certificate to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    
    # Create temporary files for the certificate and private key
    with tempfile.NamedTemporaryFile(delete=False) as cert_file, tempfile.NamedTemporaryFile(delete=False) as key_file:
        cert_file.write(certificate_pem)
        key_file.write(private_key_pem)
        cert_file_path = cert_file.name
        key_file_path = key_file.name
    
    # Using httpx client with HTTP/2 and certificate for mutual TLS
    with httpx.Client(http2=True, verify=False, cert=(cert_file_path, key_file_path)) as client:
        # Read queries from the file
        with open(queries_file, "r") as f:
            queries = [line.strip().strip('"') for line in f.readlines() if line.strip()]
        
        # Process each query
        for query in queries:
            make_request_and_save(query, client, save_location)
    
    # Clean up temporary files
    os.remove(cert_file_path)
    os.remove(key_file_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper to make HTTP/2 requests with a .p12 key and save results as JSON.")
    parser.add_argument("--p12", required=True, help="Path to the .p12 certificate file.")
    parser.add_argument("--p12_password", required=True, help="Password for the .p12 certificate file.")
    parser.add_argument("--queries_file", required=True, help="Path to the file containing queries.")
    parser.add_argument("--save_location", required=True, help="Directory to save the resulting JSON files.")
    
    args = parser.parse_args()
    
    # Create save directory if it does not exist
    os.makedirs(args.save_location, exist_ok=True)
    
    main(args.p12, args.p12_password, args.queries_file, args.save_location)
