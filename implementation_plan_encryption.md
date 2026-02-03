# IMPLEMEMTATION PLAN: HRAG Encryption Integration (Dual DB)

This plan outlines the integration of AES-GCM encryption and storing sensitive chat logs in a **Separate Secure Supabase Project**.

## 1. Prerequisites
- **Library**: Ensure `cryptography` is installed.
- **Environment**:
  - `CHAT_MASTER_KEY`: 32-byte hex for encryption.
  - `SECURE_SUPABASE_URL`: URL for the 2nd DB.
  - `SECURE_SUPABASE_KEY`: Service Role/Anon Key for the 2nd DB.

## 2. Core Security Module (`modules/security.py`)
- **Copy Logic**: From `HRAG/crypto_utils.py`.
- **Functionality**: Reliable AES-GCM Encrypt/Decrypt using `HKDF` derived keys per user.

## 3. Secure Database Client (`modules/secure_db.py`)
**Purpose**: Handle connection to the second Supabase instance.
**Logic**:
- Initialize a `Client` object using `SECURE_SUPABASE_*` env vars.
- Provide `insert_secure_chat()` and `fetch_secure_history()`.

## 4. Database Integration (`modules/conversation.py`)
**Goal**: Redirect chat storage flow to the new Secure DB.

### 4.1. Saving Messages (`_save_message`)
- **Old**: `supabase_insert("sakhi_conversations", ...)` (Main DB).
- **New**:
  1. `encrypted_payload = security.encrypt_message(user_id, message)`.
  2. `payload_json = json.dumps(encrypted_payload)`.
  3. `secure_db.insert_secure_chat(user_id, payload_json, lang, role)`.

### 4.2. Retrieving History (`get_last_messages`)
- **Old**: `supabase_select("sakhi_conversations", ...)` (Main DB).
- **New**:
  1. `rows = secure_db.fetch_secure_history(user_id)`.
  2. For each row:
     - `raw_text = row["message_text"]`.
     - `decrypted_text = security.decrypt_message(user_id, json.loads(raw_text))`.
  3. return list of decrypted history.

## 5. Verification
- **Test Script**: `scripts/test_secure_flow.py`.
  - Simulates a chat.
  - Checks if **Main DB** is empty (or metadata only).
  - Checks if **Secure DB** has encrypted blob.
  - Decrypts and verifies text matches original.

## 6. Execution Order
1.  Install `cryptography`.
2.  Create `modules/security.py`.
3.  Create `modules/secure_db.py`.
4.  Update `modules/conversation.py`.
