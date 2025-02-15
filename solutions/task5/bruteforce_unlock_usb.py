import subprocess
import string
import sys
from itertools import product

# Define the fixed prefix of the password
fixed_prefix = ";sY<TF1-EZc*v(nWO"

# Character set for brute-forcing the last two characters
charset = string.ascii_letters + string.digits + string.punctuation

# Function to attempt unlocking
def try_password(password):
    process = subprocess.Popen(['/mnt/unlock'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=f"{password}\n".encode())
    
    # Check if the output does not contain "Password incorrect."
    if b"Password incorrect." not in stdout + stderr:
        return True
    return False

# Generate all combinations of two characters from the charset
for combo in product(charset, repeat=1):
    # Form the password by appending the brute-forced characters to the fixed prefix
    password = fixed_prefix + ''.join(combo)
    
    # Try the password
    if try_password(password):
        print(f"Password found: {password}")
        sys.exit(0)  # Exit the script once a valid password is found
    else:
        print(f"Tried password: {password} - Incorrect")