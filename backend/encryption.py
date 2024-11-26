from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256

def generate_keypair():
    """Generate an RSA keypair."""
    key = RSA.generate(2048)
    private_key = key.export_key().decode()
    public_key = key.publickey().export_key().decode()
    return private_key, public_key

def encrypt_message(message, recipient_public_key):
    """Encrypt a message using the recipient's public key with SHA-256."""
    public_key = RSA.import_key(recipient_public_key.encode())
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    return cipher.encrypt(message.encode())

def decrypt_message(encrypted_message, recipient_private_key):
    """Decrypt a message using the recipient's private key with SHA-256."""
    private_key = RSA.import_key(recipient_private_key.encode())
    cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
    return cipher.decrypt(encrypted_message).decode()

if __name__ == "__main__":
    private_key, public_key = generate_keypair()
    print(f"Private Key:\n{private_key}")
    print(f"Public Key:\n{public_key}")

    message = "Hello, RSA with SHA-256!"
    encrypted = encrypt_message(message, public_key)
    print(f"Encrypted Message:\n{encrypted}")

    decrypted = decrypt_message(encrypted, private_key)
    print(f"Decrypted Message:\n{decrypted}")