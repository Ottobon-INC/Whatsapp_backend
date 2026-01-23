# modules/security.py
import os
import base64
import json
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve Master Key from Environment
# Fallback for dev/test if not set: generate a transient one (Warning: Data loss on restart!)
ENV_MASTER_KEY = os.getenv("CHAT_MASTER_KEY")
if ENV_MASTER_KEY:
    try:
        MASTER_KEY = bytes.fromhex(ENV_MASTER_KEY) if len(ENV_MASTER_KEY) == 64 else ENV_MASTER_KEY.encode()
    except ValueError:
        MASTER_KEY = ENV_MASTER_KEY.encode() # Handle non-hex string
else:
    logger.warning("⚠️ CHAT_MASTER_KEY not found in .env! Using a temporary random key. ENCRYPTED DATA WILL BE LOST ON RESTART.")
    MASTER_KEY = os.urandom(32)

def derive_user_key(user_id: str) -> bytes:
    """
    Derive a unique 32-byte AES key for a specific user using HKDF.
    """
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=user_id.encode(),
        info=b"chat_encryption",
        backend=default_backend()
    ).derive(MASTER_KEY)

def encrypt_message(user_id: str, text: str) -> dict:
    """
    Encrypts text using AES-GCM with a user-specific key.
    
    Args:
        user_id: ID of the user (used for key derivation).
        text: Plaintext message.
        
    Returns:
        dict: {"ciphertext": base64_str, "nonce": base64_str}
    """
    try:
        if not text:
            return {"ciphertext": "", "nonce": ""}

        key = derive_user_key(user_id)
        aes = AESGCM(key)
        nonce = os.urandom(12) # NIST recommended nonce size
        cipher_bytes = aes.encrypt(nonce, text.encode("utf-8"), None)

        return {
            "ciphertext": base64.b64encode(cipher_bytes).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8")
        }
    except Exception as e:
        logger.error(f"Encryption failed for user {user_id}: {e}")
        # In production, maybe raise error. For now, we prefer not to crash flow.
        return {"error": "encryption_failed"}

def decrypt_message(user_id: str, payload: dict) -> str:
    """
    Decrypts a payload (ciphertext + nonce) using the user's key.
    
    Args:
        user_id: ID of the user.
        payload: Dict containing 'ciphertext' and 'nonce'.
        
    Returns:
        str: Decrypted plaintext.
    """
    try:
        if not payload or "ciphertext" not in payload or "nonce" not in payload:
            return "[Invalid Encrypted Payload]"

        if not payload["ciphertext"]:
            return ""

        key = derive_user_key(user_id)
        aes = AESGCM(key)
        
        nonce = base64.b64decode(payload["nonce"])
        cipher_bytes = base64.b64decode(payload["ciphertext"])
        
        plaintext_bytes = aes.decrypt(nonce, cipher_bytes, None)
        return plaintext_bytes.decode("utf-8")
        
    except Exception as e:
        logger.error(f"Decryption failed for user {user_id}: {e}")
        return "[Decryption Error]"
