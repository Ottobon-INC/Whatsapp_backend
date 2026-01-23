# modules/secure_db.py
import os
import logging
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants (Retrieved from Env)
SECURE_URL = os.getenv("SECURE_SUPABASE_URL")
SECURE_KEY = os.getenv("SECURE_SUPABASE_KEY")

class SecureDBClient:
    """
    Client for interacting with the Secondary (Secure) Supabase Instance.
    Used for storing encrypted chat logs.
    """
    
    def __init__(self):
        self.client: Client = None
        if SECURE_URL and SECURE_KEY:
            try:
                self.client = create_client(SECURE_URL, SECURE_KEY)
                logger.info("✅ Connected to Secure DB (Second Supabase Instance)")
            except Exception as e:
                logger.error(f"❌ Failed to connect to secure DB: {e}")
        else:
            logger.warning("⚠️ SECURE_SUPABASE_URL or KEY missing. Secure DB features disabled.")

    def insert_secure_chat(self, payload: dict):
        """
        Insert encrypted record into 'sakhi_conversations' in Secure DB.
        """
        if not self.client:
            logger.warning("Skipping secure insert: Client not initialized.")
            return None
            
        try:
            # We assume the secure DB has table name: 'chats'
            resp = self.client.table("chats").insert(payload).execute()
            return resp.data
        except Exception as e:
            logger.error(f"Failed to insert into Secure DB: {e}")
            return None

    def fetch_secure_history(self, user_id: str, limit: int = 50):
        """
        Fetch encrypted records from Secure DB.
        """
        if not self.client:
            return []
            
        try:
            resp = self.client.table("chats")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return resp.data
        except Exception as e:
            logger.error(f"Failed to fetch secure history: {e}")
            return []

# Singleton
_secure_db_instance = None

def get_secure_db() -> SecureDBClient:
    global _secure_db_instance
    if _secure_db_instance is None:
        _secure_db_instance = SecureDBClient()
    return _secure_db_instance
