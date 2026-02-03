import os
import base64
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file explicitly to ensure we get the local key
from dotenv import load_dotenv
load_dotenv()

# Retrieve Master Key from Environment
ENV_MASTER_KEY = os.getenv("CHAT_MASTER_KEY")
if ENV_MASTER_KEY:
    try:
        # Support Hex string (64 chars) or raw string
        if len(ENV_MASTER_KEY) == 64:
             try:
                 MASTER_KEY = bytes.fromhex(ENV_MASTER_KEY)
             except ValueError:
                 MASTER_KEY = ENV_MASTER_KEY.encode()
        else:
             MASTER_KEY = ENV_MASTER_KEY.encode()
    except Exception:
        MASTER_KEY = ENV_MASTER_KEY.encode()
else:
    logger.warning("⚠️ CHAT_MASTER_KEY not found in .env! Using a temporary random key. ENCRYPTED DATA WILL BE LOST ON RESTART.")
    MASTER_KEY = os.urandom(32)

def derive_user_key(user_id: str) -> bytes:
    """
    Derive a unique 32-byte AES key for a specific user using HKDF.
    Info context is strictly b"chat".
    """
    if not user_id:
        raise ValueError("User ID required for key derivation")
        
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=user_id.encode(),
        info=b"chat", 
        backend=default_backend()
    ).derive(MASTER_KEY)

def encrypt_message(user_id: str, text: str) -> dict:
    """
    Encrypts text using AES-GCM with a user-specific key.
    Returns dict: {"ciphertext": base64_str, "nonce": base64_str}
    """
    try:
        if not text:
            # Return empty structure for empty input
            return {"ciphertext": "", "nonce": ""}

        key = derive_user_key(user_id)
        aes = AESGCM(key)
        nonce = os.urandom(12) # NIST recommended nonce size
        
        # Encrypt
        cipher_bytes = aes.encrypt(nonce, text.encode("utf-8"), None)

        return {
            "ciphertext": base64.b64encode(cipher_bytes).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8")
        }
    except Exception as e:
        logger.error(f"Encryption failed for user {user_id}: {e}")
        raise e 

def decrypt_message(user_id: str, payload: dict) -> str:
    """
    Decrypts a payload (ciphertext + nonce) using the user's key.
    Args:
        user_id: ID of the user.
        payload: Dict containing 'ciphertext' and 'nonce' (base64 strings).
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
        # Return error marker so UI knows something went wrong, but doesn't crash
        return "[Decryption Error]"
