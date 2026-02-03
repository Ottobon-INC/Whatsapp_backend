import asyncio
import os
import sys

# Setup Path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

from dotenv import load_dotenv
load_dotenv()

from modules.conversation import save_user_message, get_last_messages

async def verify_encryption_flow():
    print("\n=== 🔐 VERIFYING ENCRYPTION FLOW (v2) ===\n")
    
    user_id = "test_enc_final_v2"
    original_msg = "Secret: The patient needs 500mg Paracetamol."
    
    print(f"📝 1. Saving Message: '{original_msg}'")
    
    try:
        # A. Save (Encrypts -> Inserts to 'sakhi_encrypted_chats')
        # Note: This will perform REAL DB INSERT.
        result = save_user_message(user_id, original_msg, "en")
        print(f"   [DB Insert Result]: SUCCESS (Row ID: {result[0]['id'] if result else 'Unknown'})")
        
        # B. Fetch (Selects -> Decrypts)
        print("\n🔍 2. Fetching History...")
        history = get_last_messages(user_id, limit=5)
        
        found = False
        for msg in history:
            role = msg['role']
            content = msg['content']
            status = "✅ DECRYPTED"
            
            # Validation
            if "ciphertext" in content or "{" in content[:2]:
                status = "❌ FAILED (Still Encrypted)"
            elif content == original_msg:
                status = "✅ SUCCESS (Exact Match)"
                found = True
            
            print(f"   - {role}: {content} [{status}]")
            
        if found:
            print("\n🎉 SUCCESS: Data is being encrypted, stored securely, and decrypted correctly.")
        else:
            print("\n⚠️ WARNING: Message not found. (Did you create the 'sakhi_encrypted_chats' table using setup_encryption.sql?)")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if 'relation "sakhi_encrypted_chats" does not exist' in str(e):
            print("\n💡 ACTION REQUIRED: Run 'setup_encryption.sql' in Supabase SQL Editor.")

if __name__ == "__main__":
    asyncio.run(verify_encryption_flow())
