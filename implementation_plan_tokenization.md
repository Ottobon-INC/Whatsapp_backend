# Implementation Plan: Deterministic Hybrid Tokenization

This document outlines the implementation of a privacy-preserving tokenization system for the Sakhi Chatbot.

## 1. Architecture Overview

The system uses a **Hybrid Tokenization Strategy**:
1.  **Identity PII (Name, Phone, Email)**: Masked using **Per-User Deterministic Tokens** (e.g., `{{PERSON_1}}`). 
    *   *Deterministic*: If User A says "Hari" twice, it maps to the same token `{{PERSON_1}}`.
    *   *Secure*: Values are AES-256 Encrypted in the vault.
2.  **Medical Terms (PCOS, IVF)**: Masked using **Global Consistent Tokens** (e.g., `{{GMED_1}}`).
    *   *Global*: "PCOS" maps to `{{GMED_1}}` for ALL users.
    *   *Analytic*: Allows counting aggregated stats on anonymous data.

---

## 2. Database Schema

### A. PII Vault (Identity)
Table: `sakhi_pii_vault`
- `user_id`: UUID (Scope)
- `value_hash`: VARCHAR (SHA256 of value for fast lookup)
- `token_key`: VARCHAR (e.g., `{{PERSON_1}}`)
- `encrypted_value`: TEXT (AES Encrypted)
- `entity_type`: VARCHAR (NAME/PHONE)

### B. Medical Dictionary (Global)
Table: `sakhi_medical_dictionary`
- `term_hash`: VARCHAR (SHA256 of term)
- `token_key`: VARCHAR (e.g., `{{GMED_1}}`)
- `encrypted_term`: TEXT (AES Encrypted)

---

## 3. Module Design (`modules/security.py`)

### Core Class: `SecurityManager`

#### Methods:
1.  **`mask_hybrid(text, user_id) -> str`**
    -   **Step 1 (Medical)**: Scans for keywords. Checks Global Cache/DB. Replaces with `{{GMED_X}}`.
    -   **Step 2 (Identity)**: Scans for Regex. Calculates Hash. Checks Personal Vault. Replaces with `{{PERSON_X}}`.
    -   *Returns*: Fully masked string for DB storage.

2.  **`unmask_medical_only(text) -> str`**
    -   Scans for `{{GMED_X}}`.
    -   Lookups value (PCOS).
    -   Replaces token with value.
    -   *Leaves {{PERSON_X}} alone*.
    -   *Returns*: Partially unmasked string for LLM Context.

---

## 4. Workflows

### Inbound Message (User -> DB)
1.  User sends: `"I am Anu, I have PCOS"`
2.  `conversation.py` calls `security.mask_hybrid(msg, user_id)`.
3.  **Medical**: "PCOS" found. Global token `{{GMED_5}}` retrieved.
4.  **Identity**: "Anu" found. Hash `a7fb` calculated. Vault checked.
    -   *Found*: Return `{{PERSON_1}}`.
    -   *New*: Create `{{PERSON_1}}`, Insert `a7fb` + Encrypted("Anu").
5.  **Save to DB**: `"I am {{PERSON_1}}, I have {{GMED_5}}"`

### Outbound Context (DB -> LLM)
1.  App fetches history: `"I am {{PERSON_1}}, I have {{GMED_5}}"`
2.  `conversation.py` calls `security.unmask_medical_only(msg)`.
3.  **Medical**: `{{GMED_5}}` -> "PCOS".
4.  **Identity**: `{{PERSON_1}}` -> Ignored.
5.  **Send to LLM**: `"I am {{PERSON_1}}, I have PCOS"`

---

## 5. Setup Instructions

1.  **Dependencies**: `pip install cryptography`
2.  **Env**: Set `PII_SECRET_KEY` in `.env`.
3.  **Migration**: Run SQL from `sql/create_security_tables.sql`.
