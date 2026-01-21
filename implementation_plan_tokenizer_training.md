# IMPLEMENTATION PLAN: Custom Telugu Tokenizer Training

## 1. Objective
Create a highly efficient **SentencePiece (Unigram)** tokenizer tailored specifically for:
- **Telugu Language** (Mixed with English/Tinglish).
- **Medical Domain** (IVF, IUI, Pregnancy terms).

## 2. Input Data Strategy
We need a "corpus" (a large text file) to teach the tokenizer. We will combine:
1.  **Existing Knowledge Base**: `data/cleaned_sections.json` (Your medical content).
2.  **FAQ Data**: `data/faqs.json` (Your Q&A pairs).
3.  **Synthetic Telugu**: We will generate/append some common Telugu text references if available, or rely on the fact that your content is already mixed. 
    *   *Note: If your JSONs are purely English, the tokenizer will learn English. We must ensure we have Telugu text coverage or accept an English-optimized Unigram model.*

## 3. The Script (`scripts/train_tokenizer.py`)
This script will perform three steps:
1.  **Extract Text**: Read all text fields (content, headers, questions, answers) from your JSON data files.
2.  **Clean & Format**: Save them into a single raw text file (`corpus_for_training.txt`).
3.  **Train Model**: Use `sentencepiece.SentencePieceTrainer.train()` with:
    - `model_type="unigram"` (The goal).
    - `vocab_size=8000` (Sufficient for a specialized bot).
    - `character_coverage=1.0` (To ensure all emojis/chars are kept).

## 4. Execution Pipeline
1.  **Run Script**: `python scripts/train_tokenizer.py`
2.  **Output**: It will generate `modules/assets/telugu.model` and `modules/assets/telugu.vocab`.
3.  **Verify**: Small test function to print tokens for "IVF ఖర్చు ఎంత?".

## 5. Integration
- The existing `tokenizer_manager.py` already logic looks for `modules/assets/telugu.model`.
- Once generated, no code changes are needed—it just starts working!

## 6. Verification
We will run a comparison:
- **Input**: "IVF process is safe"
- **OpenAI**: `[IVF, process, is, safe]` (4 tokens)
- **Custom**: `[IVF process, is safe]` (Maybe 2 tokens if frequent)

**Ready to creating the training script.**
