import os
import json
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Signature import pss 
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes


# ----------------------------------------------------------------------
# 1) Keypair Generation
# ----------------------------------------------------------------------
def generate_keypair(bits=2048):
    """
    Generate an RSA key pair (private + public) as PEM-encoded strings.
    By default, 2048-bit keys are generated. For stronger security, 
    you may use 3072 or 4096 bits, but performance will suffer.
    """
    key = RSA.generate(bits)
    private_key_pem = key.export_key().decode("utf-8")
    public_key_pem = key.publickey().export_key().decode("utf-8")
    return private_key_pem, public_key_pem


# ----------------------------------------------------------------------
# 2) Encrypt / Decrypt RSA Private Key with Password (AES GCM)
# ----------------------------------------------------------------------
def encrypt_private_key(private_key_pem, password):
    """
    Encrypt the *PEM-encoded* RSA private key using a password-derived AES key.
    Returns a base64-encoded JSON string containing salt, nonce, tag, and ciphertext.
    
    - PBKDF2 is used to derive a 256-bit AES key from the password + random salt.
    - AES-GCM is used for authenticated encryption.
    - The final output is JSON-serialized then base64-encoded, so it can be stored or sent easily.
    """
    salt = get_random_bytes(16)
    aes_key = PBKDF2(password, salt, dkLen=32, count=100_000)  # 100k iterations
    cipher = AES.new(aes_key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(private_key_pem.encode("utf-8"))

    package = {
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(cipher.nonce).decode(),
        "tag": base64.b64encode(tag).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }
    package_json = json.dumps(package)
    return base64.b64encode(package_json.encode("utf-8")).decode("utf-8")


def decrypt_private_key(encrypted_str, password):
    """
    Decrypt the base64-encoded JSON produced by encrypt_private_key().
    Returns the original PEM-encoded RSA private key as a string.
    
    Raises an exception if:
      - The password is incorrect (tag verification fails).
      - The data is malformed.
    """
    package_json = base64.b64decode(encrypted_str.encode("utf-8")).decode("utf-8")
    package = json.loads(package_json)

    salt = base64.b64decode(package["salt"].encode("utf-8"))
    nonce = base64.b64decode(package["nonce"].encode("utf-8"))
    tag = base64.b64decode(package["tag"].encode("utf-8"))
    ciphertext = base64.b64decode(package["ciphertext"].encode("utf-8"))

    aes_key = PBKDF2(password, salt, dkLen=32, count=100_000)
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)

    return decrypted_bytes.decode("utf-8")


# ----------------------------------------------------------------------
# 3) RSA Message Encryption / Decryption (with OAEP + SHA256)
# ----------------------------------------------------------------------
def encrypt_message(plaintext, recipient_public_key_pem):
    """
    Encrypts a plaintext message (string) using the recipient's RSA public key (PEM).
    Returns raw ciphertext bytes.
    
    Typically, you'll hex-encode this when sending it over JSON or a network. 
    Example: ciphertext.hex()
    """
    public_key = RSA.import_key(recipient_public_key_pem)
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    ciphertext = cipher.encrypt(plaintext.encode("utf-8"))
    return ciphertext


def decrypt_message(ciphertext_bytes, recipient_private_key_pem):
    """
    Decrypts ciphertext bytes (produced by encrypt_message) using the RSA private key (PEM).
    Returns the decrypted plaintext as a string.
    
    If the ciphertext is invalid or the key is incorrect, it raises an exception.
    """
    private_key = RSA.import_key(recipient_private_key_pem)
    cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
    plaintext_bytes = cipher.decrypt(ciphertext_bytes)
    return plaintext_bytes.decode("utf-8")


# ----------------------------------------------------------------------
# 4) RSA Message Signing / Verification (with PSS + SHA256)
# ----------------------------------------------------------------------
def sign_message(plaintext, signer_private_key_pem):
    """
    Example of signing with RSA-PSS.
    """
    private_key = RSA.import_key(signer_private_key_pem)
    h = SHA256.new(plaintext.encode("utf-8"))
    signer = pss.new(private_key)  # <--- use pss.new
    signature = signer.sign(h)
    return signature


def verify_signature(plaintext, signature_bytes, signer_public_key_pem):
    """
    Example of verifying an RSA-PSS signature.
    """
    public_key = RSA.import_key(signer_public_key_pem)
    h = SHA256.new(plaintext.encode("utf-8"))
    verifier = pss.new(public_key)
    try:
        verifier.verify(h, signature_bytes)
        return True
    except (ValueError, TypeError):
        return False


# ----------------------------------------------------------------------
# Example usage (comment out if you only want library functions)
# ----------------------------------------------------------------------

# if __name__ == "__main__":
#     # Generate a new key pair
#     # priv_key, pub_key = generate_keypair()
#     # print("[*] Generated RSA Keypair.")
#     # print("Private Key (PEM) starts with:", priv_key[:50], "...")
#     # print("Public Key (PEM) starts with:", pub_key[:50], "...")

#     # password = "My$uperSecretPassphrase"
#     # encrypted_priv = encrypt_private_key(priv_key, password)
#     # print("\n[*] Encrypted Private Key (base64+JSON):", encrypted_priv[:80], "...")

#     # decrypted_priv = decrypt_private_key(encrypted_priv, password)
#     # print("[*] Decrypted Private Key matches original?", decrypted_priv == priv_key)

#     # message = "Hello, RSA!"
#     # ciphertext = encrypt_message(message, pub_key)
#     # print("\n[*] Ciphertext (hex) =", ciphertext.hex()[:64], "...")
#     # decrypted_msg = decrypt_message(ciphertext, priv_key)
#     # print("[*] Decrypted message:", decrypted_msg)

#     # signature = sign_message(message, priv_key)
#     # is_valid = verify_signature(message, signature, pub_key)
#     # print("[*] Signature valid:", is_valid)
