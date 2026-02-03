# Implementation Plan: Secure End-to-End Chat Encryption

## Objective
Integrate AES-256-GCM encryption into the existing `sakhi` chatbot backend to ensure zero-trust storage. Messages will be encrypted using unique per-user keys derived from a Master Key before being stored in the database.

## 1. Core Principles
*   **Algorithm**: AES-256-GCM (Authenticated Encryption).
*   **Key Derivation**: HKDF (SHA-256) using `CHAT_MASTER_KEY` + `user_id` (Salt) + `info=b"chat"`.
*   **Storage**: Encrypted payloads (`ciphertext`, `nonce`) stored in a dedicated table. **No plaintext stored.**
*   **Transparency**: Chatbot logic (RAG, SLM, Routing) remains 100% unaware of encryption.

## 2. Infrastructure Changes

### 2.1. Environment Variables
Ensure `.env` contains:
```ini
CHAT_MASTER_KEY=your_64_char_hex_key_here
```

### 2.2. Database Schema
Create a dedicated table to isolate encrypted logs from legacy data:
```sql
create table if not exists sakhi_encrypted_chats (
  id uuid default gen_random_uuid() primary key,
  user_id text not null,
  role text not null,        -- 'user' or 'sakhi'
  ciphertext text not null,  -- Base64 encoded encrypted content
  nonce text not null,       -- Base64 encoded nonce (12 bytes)
  language text default 'en',
  created_at timestamptz default now()
);
create index idx_enc_chats_user on sakhi_encrypted_chats(user_id);
```

## 3. Code Implementation Steps

### Step 1: Create Security Module (`modules/security.py`)
Implement the cryptographic primitives.
*   **Dependencies**: `cryptography`
*   **Functions**:
    *   `derive_user_key(user_id)`: Implements HKDF logic.
    *   `encrypt_message(user_id, text)`: Returns `{ciphertext, nonce}`.
    *   `decrypt_message(user_id, payload)`: Returns plaintext `str`.

### Step 2: Update Conversation Module (`modules/conversation.py`)
Intercept database calls to inject encryption.
*   **Save Flow (`_save_message`)**:
    1.  Receive plaintext message.
    2.  Call `encrypt_message(user_id, text)`.
    3.  Insert into `sakhi_encrypted_chats` (target table change).
    4.  **Do NOT** insert into legacy `sakhi_conversations`.
*   **Fetch Flow (`get_last_messages`)**:
    1.  Select from `sakhi_encrypted_chats`.
    2.  For each row, call `decrypt_message`.
    3.  Return plaintext list to `main.py`.

### Step 3: Verification
Create a script `scripts/verify_encryption.py` that:
1.  Simulates a user message.
2.  Encrypts & Inserts it into the DB.
3.  Reads it back & Decrypts it.
4.  Asserts `Decrypted == Original`.

## 4. Rollback Strategy
If issues arise:
1.  Revert `modules/conversation.py` to point back to `sakhi_conversations` table.
2.  Disable `modules/security.py` imports.
