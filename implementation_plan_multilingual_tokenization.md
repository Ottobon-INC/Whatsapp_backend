# IMPLEMEMTATION PLAN: Multilingual Tokenization & Hybrid Architecture

This plan outlines the steps to upgrade "Sakhi" from a monolithic OpenAI wrapper to a robust, cost-effective hybrid system (GPT + SLM) with explicit tokenization control.

## 1. Prerequisites & Dependencies

### 1.1 New Python Packages
Update `requirements.txt` to include necessary libraries for tokenization and translation.

- **sentencepiece**: For Telugu-optimized tokenization (SLM pipeline).
- **deep-translator**: For Query Translation (Telugu -> English).

**Action:**
Add to `requirements.txt`:
```text
sentencepiece==0.1.99
deep-translator==1.11.4
```

### 1.2 Model Files
- **Action**: A generic `sentencepiece` model (e.g., Llama-3's tokenizer or a custom Telugu one) needs to be placed in `modules/assets/`. For this plan, we will assume using a standard Multilingual Llama tokenizer or a mock if the file isn't available.

## 2. Core Modules Implementation

### 2.1 New Module: `tokenizer_manager.py`
**Purpose**: Centralize tokenization logic. Avoid mixing `tiktoken` (OpenAI) and `SentencePiece` (SLM).

**Logic**:
- Class `SakhiTokenizer`:
  - `encode_for_gpt(text)`: Uses `tiktoken` (cl100k_base). Returns token count.
  - `encode_for_slm(text)`: Uses `sentencepiece`. Returns tokenized text segments.
  - `truncate_for_slm(text, limit=1024)`: Smart truncation preserving Telugu semantic units.

### 2.2 New Module: `translation_service.py`
**Purpose**: Handle "Query Translation" for RAG.

**Logic**:
- Function `translate_query(text, source_lang, target_lang="en")`:
  - Checks if text is already English.
  - Calls Translation API (deep-translator).
  - Returns English text for Vector Search.

## 3. Refactoring Existing Modules

### 3.1 Update `rag_search.py` (or `search_hierarchical.py`)
**Current**: Embeds raw user query -> Search.
**New**:
1. Check User Language.
2. If Telugu/Tinglish: Call `translate_query()` -> English Query.
3. Embed English Query -> Search.
4. Return Context (English).

### 3.2 Update `slm_client.py`
**Current**: Has basic prompts.
**New**:
- Add **Tokenization Guard**: Before sending to SLM API, run `SakhiTokenizer.truncate_for_slm`.
- Ensure System Prompt strictly adheres to the "Language Lock".

### 3.3 Update `model_gateway.py` (The Router)
Ensure the routing logic aligns with the report:
- **Emergency / Complex Medical** -> GPT-4.
- **Smalltalk / Simple FAQ** -> SLM.
- **Verify**: Ensure the keywords/embeddings used for routing are language-agnostic (or translated before routing check).

## 4. Integration Logic (in `main.py`)

Refactor `sakhi_chat` endpoint to follow the new "Pipeline":

1. **Normalize**: Clean input.
2. **Translate (for Internal Logic)**: Create an `english_intent_query` using `translation_service`.
3. **Route**: Use `english_intent_query` to decide Gateway Route (GPT vs SLM).
4. **Execute**:
   - **Case SLM_RAG**:
     - `context` = `hierarchical_rag_query(english_intent_query)` (Search uses exact English match)
     - `response` = `slm_client.generate_rag_response(context, user_original_message_raw, target_lang)`
   - **Case GPT_RAG**:
     - `response` = `generate_medical_response(user_original_message_raw)` (Integrated translation or smart GPT handling).

## 5. Verification Steps

1. **Test Tokenizer**: Run a script comparing `tiktoken` vs `sentencepiece` count on a Telugu string.
2. **Test Translation**: Verify `IVF entha?` becomes `How much is IVF?` before hitting the database.
3. **Test End-to-End**: Ensure a Telugu question gets a Telugu answer, but uses English context docs.
