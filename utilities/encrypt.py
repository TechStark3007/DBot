from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Util.Padding import unpad
import os
from dotenv import load_dotenv
import base64
import hashlib

load_dotenv()
key = os.getenv('AES_KEY')

def random_iv_vector() -> str:
    """Generates a secure 16-byte IV and encodes it in base64."""
    return os.urandom(16) # 16 random bytes

#ENCRYPT AES
def encrypt_aes(text: str) -> str:
    """Encrypts a string using AES encryption with a user-specified key.
    
    Args:
        text (str): The string to encrypt.
    
    Returns:
        str: The encrypted string in base64 format.
    """
    # Convert the key to 32 bytes (AES-256)
    key_bytes = hashlib.sha256(key.encode()).digest()

    # Generate a random IV (Initialization Vector)
    iv = random_iv_vector()  

    # Create AES cipher
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)

    # Pad the text and encrypt
    encrypted_bytes = cipher.encrypt(pad(text.encode(), AES.block_size))

    # Return base64-encoded ciphertext (IV + encrypted data)
    return base64.b64encode(iv + encrypted_bytes).decode()



#DECRYPT AES
def decrypt_aes(encrypted_text: str) -> str:
    """Decrypts a base64-encoded AES-encrypted string using a user-specified key.
    
    Args:
        encrypted_text (str): The base64-encoded encrypted string.
        key (str): The decryption key (must be the same as used for encryption).
    
    Returns:
        str: The decrypted string.
    """
    # Convert the key to 32 bytes (AES-256)
    key_bytes = hashlib.sha256(key.encode()).digest()

    # Decode base64 string
    encrypted_data = base64.b64decode(encrypted_text)

    # Extract IV (first 16 bytes)
    iv = encrypted_data[:16]
    encrypted_bytes = encrypted_data[16:]

    # Create AES cipher
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)

    # Decrypt and remove padding
    decrypted_text = unpad(cipher.decrypt(encrypted_bytes), AES.block_size).decode()

    return decrypted_text


encrypted_text = encrypt_aes("Hello, AES Encryption!")
print("Encrypted:", encrypted_text)


decrypted_text = decrypt_aes(encrypted_text)
print("Decrypted:", decrypted_text)
