import os
import re
import base64
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Internal imports
from supabase_client import supabase_insert, supabase_select, supabase_update
from modules.pii_keywords import MEDICAL_KEYWORDS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CRYPTO UTILS
# ============================================================================

def _get_fernet() -> Fernet:
    secret = os.getenv("PII_SECRET_KEY")
    # Dev fallback
    if not secret: 
        logger.warning("PII_SECRET_KEY missing. Using insecure Dev key.")
        secret = "dev_static_secret_key_123_must_be_changed_in_prod"

    if len(secret) < 32: # Pad if too short for KDF input safety
        secret = secret + "0"*(32-len(secret))

    if len(secret) != 44 or not secret.endswith("="):
            salt = b'sakhi_static_salt' 
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
            key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    else:
            key = secret.encode()
    return Fernet(key)

def encrypt_val(text: str) -> str:
    if not text: return text
    return _get_fernet().encrypt(text.encode()).decode()

def decrypt_val(cipher: str) -> str:
    if not cipher: return cipher
    try: return _get_fernet().decrypt(cipher.encode()).decode()
    except: return "[Error]"

def hash_val(val: str) -> str:
    """SHA256 hash for fast lookup."""
    return hashlib.sha256(val.lower().encode()).hexdigest()

# ============================================================================
# SECURITY MANAGER (DETERMINISTIC)
# ============================================================================

class SecurityManager:
    
    def __init__(self):
        # In-Memory Cache for Global Medical Tokens
        self.med_token_cache = {} # { hash: {{GMED_1}} }
        self.med_reverse_cache = {} # { {{GMED_1}}: "pcos" }
        self.ephemeral_cache = {} # { {{PERSON_...}}: "Deepthi" } - Fallback if DB fails
        self._load_global_dictionary()

    def _load_global_dictionary(self):
        """Pre-load global medical tokens."""
        try:
            rows = supabase_select("sakhi_medical_dictionary", select="token_key, term_hash, encrypted_term")
            if rows:
                for r in rows:
                    t_key, t_hash = r.get("token_key"), r.get("term_hash")
                    if t_key and t_hash:
                        self.med_token_cache[t_hash] = t_key
                        # Decrypt lazily or eager? Eager for speed
                        enc = r.get("encrypted_term")
                        if enc:
                            self.med_reverse_cache[t_key] = decrypt_val(enc)
        except Exception as e:
            logger.error(f"Failed to load medical dictionary: {e}")

    # --- PUBLIC API ---

    def mask_hybrid(self, text: str, user_id: str) -> str:
        """
        1. Mask Medical (Global Deterministic)
        2. Mask Identity (User-Scoped Deterministic)
        """
        if not text: return text
        
        # 1. Medical
        masked = self._mask_medical_global(text)
        
        # 2. Identity
        masked = self._mask_identity_deterministic(masked, user_id)
        
        return masked

    def unmask_medical_only(self, text: str) -> str:
        """Restores only Medical terms for LLM."""
        if not text: return text
        tokens = re.findall(r'(\{\{GMED_\d+\}\})', text)
        result = text
        for tok in set(tokens):
            if tok in self.med_reverse_cache:
                result = result.replace(tok, self.med_reverse_cache[tok])
        return result

    # --- INTERNAL LOGIC ---
    
    # ... (skipping _mask_medical_global and _get_or_create_global_token for brevity in replacement if possible, but replace_file_content requires contiguous)
    # Actually I need to target _get_or_create_pii_token and unmask_pii specifically.
    # The user asked to go through codebase. I will just replace the methods.
    # But I need to change __init__ too.
    # So I will use MultiReplace.


    def _load_global_dictionary(self):
        """Pre-load global medical tokens."""
        try:
            rows = supabase_select("sakhi_medical_dictionary", select="token_key, term_hash, encrypted_term")
            if rows:
                for r in rows:
                    t_key, t_hash = r.get("token_key"), r.get("term_hash")
                    if t_key and t_hash:
                        self.med_token_cache[t_hash] = t_key
                        # Decrypt lazily or eager? Eager for speed
                        enc = r.get("encrypted_term")
                        if enc:
                            self.med_reverse_cache[t_key] = decrypt_val(enc)
        except Exception as e:
            logger.error(f"Failed to load medical dictionary: {e}")

    # --- PUBLIC API ---

    def mask_hybrid(self, text: str, user_id: str) -> str:
        """
        1. Mask Medical (Global Deterministic)
        2. Mask Identity (User-Scoped Deterministic)
        """
        if not text: return text
        
        # 1. Medical
        masked = self._mask_medical_global(text)
        
        # 2. Identity
        masked = self._mask_identity_deterministic(masked, user_id)
        
        return masked

    def unmask_medical_only(self, text: str) -> str:
        """Restores only Medical terms for LLM."""
        if not text: return text
        tokens = re.findall(r'(\{\{GMED_\d+\}\})', text)
        result = text
        for tok in set(tokens):
            if tok in self.med_reverse_cache:
                result = result.replace(tok, self.med_reverse_cache[tok])
        return result

    # --- INTERNAL LOGIC ---

    def _mask_medical_global(self, text: str) -> str:
        new_text = text
        sorted_kw = sorted(MEDICAL_KEYWORDS, key=len, reverse=True)
        
        for word in sorted_kw:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(new_text))
            if not matches: continue
            
            w_hash = hash_val(word)
            
            # Cache Hit?
            if w_hash in self.med_token_cache:
                token = self.med_token_cache[w_hash]
            else:
                # DB Hit or Create
                token = self._get_or_create_global_token(word, w_hash)
            
            new_text = pattern.sub(token, new_text)
            
        return new_text

    def _get_or_create_global_token(self, term: str, w_hash: str) -> str:
        # Check DB first in case another instance created it
        try:
            rows = supabase_select("sakhi_medical_dictionary", select="token_key", filters=f"term_hash=eq.{w_hash}")
            if rows:
                token = rows[0]["token_key"]
                
                # RECOVERY: If token is None (bad state), fix it now
                if not token:
                     # We need the ID to update it
                     rows_full = supabase_select("sakhi_medical_dictionary", select="id", filters=f"term_hash=eq.{w_hash}")
                     if rows_full:
                         row_id = rows_full[0]['id']
                         token = f"{{{{GMED_{row_id}}}}}"
                         supabase_update("sakhi_medical_dictionary", f"id=eq.{row_id}", {"token_key": token})
                
                if token:
                    self.med_token_cache[w_hash] = token
                    self.med_reverse_cache[token] = term.lower()
                    return token
        except: pass

        # Create New
        try:
             # We let DB auto-increment ID
             enc_term = encrypt_val(term.lower())
             payload = {"term_hash": w_hash, "encrypted_term": enc_term}
             data = supabase_insert("sakhi_medical_dictionary", payload)
             
             if data and isinstance(data, list):
                 rec = data[0]
                 new_id = rec.get('id')
                 token = f"{{{{GMED_{new_id}}}}}"
                 
                 # UPDATE the DB with the generated token
                 try:
                     print(f"DEBUG: Updating ID={new_id} -> {token}")
                     supabase_update("sakhi_medical_dictionary", f"id=eq.{new_id}", {"token_key": token})
                 except Exception as up_err:
                     print(f"ERROR: {up_err}")
                     logger.error(f"Failed to update token_key: {up_err}")
                 
                 self.med_token_cache[w_hash] = token
                 self.med_reverse_cache[token] = term.lower()
                 return token
        except Exception as e:
            logger.error(f"Error creating global token: {e}")
            return "{{GMED_ERR}}"
            
        return "{{GMED_ERR}}"

    def _mask_identity_deterministic(self, text: str, user_id: str) -> str:
        masked = text
        
        # 1. Fetch User's Real Name to mask simple occurrences (context-free)
        try:
            # We use a raw select to avoid circular dependency with user_profile.py if any
            rows = supabase_select("sakhi_users", select="name", filters=f"user_id=eq.{user_id}")
            if rows:
                real_name = rows[0].get("name")
                if real_name and len(real_name.strip()) > 2: # Ignore short names to avoid false positives
                    # Case-insensitive replacement
                    pattern = re.compile(re.escape(real_name), re.IGNORECASE)
                    if pattern.search(masked):
                         token = self._get_or_create_pii_token(real_name, "PERSON", user_id)
                         masked = pattern.sub(token, masked)
        except Exception as e:
            logger.warning(f"Failed to fetch user name for masking: {e}")

        patterns = [
            (r'(?:\+91[\-\s]?)?[6-9]\d{9}', "PHONE"),
            (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "EMAIL"),
            (r'(?i)(?:my name is|i am|iam|this is)\s+([a-zA-Z]+(?:\s[a-zA-Z]+)?)', "PERSON")
        ]
        
        for regex, label in patterns:
            # We must iterate one by one to avoid overlapping complications
            # Find all
            matches = list(re.finditer(regex, masked))
            
            # Map value -> token
            val_map = {} 
            for m in matches:
                val = m.group(1) if len(m.groups()) > 0 else m.group(0)
                if val not in val_map:
                    val_map[val] = self._get_or_create_pii_token(val, label, user_id)
            
            # Replace
            for val, token in val_map.items():
                masked = masked.replace(val, token)
                
        return masked

    def _get_or_create_pii_token(self, value: str, label: str, user_id: str) -> str:
        w_hash = hash_val(value)
        
        # 1. Check DB (Vault)
        try:
            rows = supabase_select("sakhi_pii_vault", select="token_key", 
                                   filters=f"user_id=eq.{user_id}&value_hash=eq.{w_hash}")
            if rows:
                token = rows[0]["token_key"]
                self.ephemeral_cache[token] = value # Cache for immediate use
                return token
        except: pass
        
        # 2. Create New (PERSISTENT - WITH DB WRITE)
        suffix = w_hash[:6] 
        token = f"{{{{{label}_{suffix}}}}}"
        self.ephemeral_cache[token] = value # Critical: Save to cache immediately
        
        try:
            payload = {
                "user_id": user_id,
                "token_key": token,
                "value_hash": w_hash,
                "encrypted_value": encrypt_val(value),
                "entity_type": label
            }
            supabase_insert("sakhi_pii_vault", payload)
        except Exception as e:
            logger.error(f"Error saving PII: {e}")
            
        return token
    
    def mask_name_direct(self, name: str, user_id: str) -> str:
        """Explicitly mask a name string as a PERSON token."""
        if not name or not user_id:
            return name
        return self._get_or_create_pii_token(name, "PERSON", user_id)
        
    def unmask_pii(self, text: str, user_id: str) -> str:
        """Restores PII from the user's private vault."""
        if not text: return text
        
        result = text
        
        # STRATEGY 0: Clean up potential LLM bad formatting of tokens for consistency
        # e.g. {{ PERSON_123 }} -> {{PERSON_123}}
        result = re.sub(r'\{\{\s*([A-Z]+_[a-zA-Z0-9]+)\s*\}\}', r'{{\1}}', result)
        
        # STRATEGY 1: Regex Match (Fast)
        tokens = re.findall(r'(\{\{[A-Z]+_[a-zA-Z0-9]+\}\})', result)
        
        if tokens:
            for tok in set(tokens):
                # A. Check Ephemeral Cache FIRST (Fast & Fallback-proof)
                if tok in self.ephemeral_cache:
                    result = result.replace(tok, self.ephemeral_cache[tok])
                    continue
                
                # B. Check DB
                try:
                    rows = supabase_select("sakhi_pii_vault", select="encrypted_value",
                                           filters=f"user_id=eq.{user_id}&token_key=eq.{tok}")
                    if rows:
                        real_val = decrypt_val(rows[0]["encrypted_value"])
                        self.ephemeral_cache[tok] = real_val # Cache it
                        result = result.replace(tok, real_val)
                except Exception as e:
                    logger.error(f"Error unmasking token {tok}: {e}")
        
        # STRATEGY 2: Fallback - Fetch ALL tokens for this user if '{{' still exists
        if "{{" in result:
             try:
                # Fetch all tokens for this user
                all_tokens = supabase_select("sakhi_pii_vault", select="token_key, encrypted_value", 
                                            filters=f"user_id=eq.{user_id}")
                if all_tokens:
                    for item in all_tokens:
                        t_key = item.get("token_key")
                        enc_val = item.get("encrypted_value")
                        if t_key and enc_val and t_key in result:
                            real_val = decrypt_val(enc_val)
                            self.ephemeral_cache[t_key] = real_val
                            result = result.replace(t_key, real_val)
             except Exception as e:
                pass
                
        return result

_inst = None
def get_security_manager():
    global _inst
    if not _inst: _inst = SecurityManager()
    return _inst
