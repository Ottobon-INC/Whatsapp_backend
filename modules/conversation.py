# modules/conversation.py
from datetime import datetime
import uuid
import logging
# Import Security Module - Ensure this module exists!
from modules.security import encrypt_message, decrypt_message
from supabase_client import supabase_insert, supabase_select

logger = logging.getLogger(__name__)

# TABLE CONSTANTS
# We divert to a dedicated table for encrypted logs to avoid polluting legacy plaintext tables
ENCRYPTED_TABLE = "sakhi_encrypted_chats"

def _save_message(user_id: str, message: str, lang: str, message_type: str, chat_id: str | None = None):
    """
    Encrypts the message and stores only the ciphertext (+nonce) in the database.
    Retains 'user_id' and metadata for routing/history, but content is opaque.
    """
    if not message:
        print("DEBUG: _save_message called with empty message")
        return None

    print(f"DEBUG: Attempting to save message for user: {user_id}") # DEBUG TRACE

    try:
        # 1. Encrypt Content
        # Returns: {"ciphertext": "...", "nonce": "..."}
        encrypted_payload = encrypt_message(user_id, message)
        
        # 2. Prepare DB Record
        record = {
            "user_id": user_id,
            "role": message_type,  # 'user' or 'sakhi'/'assistant'
            "message_content": encrypted_payload["ciphertext"], # Matches DB Schema
            "nonce": encrypted_payload["nonce"],
            "language": lang,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if chat_id:
            record["chat_id"] = chat_id
            
        # 3. Insert into Secure Table
        res = supabase_insert(ENCRYPTED_TABLE, record)
        print(f"DEBUG: Successfully inserted record into {ENCRYPTED_TABLE}")
        return res
        
    except Exception as e:
        # LOGGING AND PRINTING for debug visibility
        error_msg = f"❌ CRITICAL DB ERROR in _save_message: {e}"
        print(error_msg) # Force output to console
        logger.error(error_msg)
        # We do NOT save plaintext fallback. We fail safe (log error, save nothing).
        # Re-raise exception so main.py knows it failed!
        raise e


def save_user_message(user_id: str, text: str, lang: str = "en"):
    return _save_message(user_id, text, lang, "user")


def save_sakhi_message(user_id: str, text: str, lang: str = "en"):
    chat_id = str(uuid.uuid4())
    # Standardize intent/role to match usage. 'sakhi' effectively means 'assistant'.
    return _save_message(user_id, text, lang, "sakhi", chat_id=chat_id)


def save_conversation(user_id: str, message: str, message_type: str, language: str):
    return _save_message(user_id, message, language, message_type)


def get_last_messages(user_id: str, limit: int = 5):
    """
    Fetch encrypted history, Decrypt per-message, and return Plaintext to the runtime.
    """
    # 1. Fetch Encrypted Rows
    rows = supabase_select(
        ENCRYPTED_TABLE,
        select="user_id, role, message_content, nonce, created_at", # Select columns explicitly
        filters=f"user_id=eq.{user_id}",
        limit=50, 
    )

    if not rows or not isinstance(rows, list):
        return []

    # 2. Sort & Decrypt
    # Sort by time Descending (newest first) -> take limit -> reverse back to Oldest-First
    sorted_rows = sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)
    recent = sorted_rows[:limit]

    history = []
    for r in reversed(recent):
        role = r.get("role")
        
        # Decrypt
        try:
            payload = {
                "ciphertext": r.get("message_content"), # Map DB column back to payload key
                "nonce": r.get("nonce")
            }
            plaintext = decrypt_message(user_id, payload)
        except Exception as e:
            logger.error(f"Decryption error for msg {r.get('created_at')}: {e}")
            plaintext = "[Encrypted Content Unavailable]"

        history.append({"role": role, "content": plaintext})

    return history
