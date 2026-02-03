
import os
import logging
import tiktoken

try:
    import sentencepiece as spm
except ImportError:
    spm = None

logger = logging.getLogger(__name__)

DEFAULT_SLM_MODEL_PATH = "modules/assets/telugu.model"

class SakhiTokenizer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SakhiTokenizer, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 1. Setup OpenAI Tokenizer (Tiktoken) - Robust
        try:
            self.gpt_encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.gpt_encoding = None
            logger.warning("Tiktoken encoding not found. GPT counting will be inaccurate.")

        # 2. Setup SLM Tokenizer (SentencePiece) - Specialized
        self.sp_processor = None
        if spm and os.path.exists(DEFAULT_SLM_MODEL_PATH):
            try:
                self.sp_processor = spm.SentencePieceProcessor(model_file=DEFAULT_SLM_MODEL_PATH)
                logger.info(f"Loaded SLM Tokenizer from {DEFAULT_SLM_MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to load SLM Tokenizer: {e}")
        else:
            logger.warning(f"SLM Tokenizer model not found at {DEFAULT_SLM_MODEL_PATH}. Using whitespace fallback.")

    def encode_for_gpt(self, text: str):
        if self.gpt_encoding:
            return self.gpt_encoding.encode(text)
        return text.split() # Fallback

    def count_tokens_gpt(self, text: str) -> int:
        if self.gpt_encoding:
            return len(self.gpt_encoding.encode(text))
        return len(text.split())

    def encode_for_slm(self, text: str):
        if self.sp_processor:
            return self.sp_processor.encode(text, out_type=str)
        return text.split()

    def count_tokens_slm(self, text: str) -> int:
        if self.sp_processor:
            return len(self.sp_processor.encode(text))
        return len(text.split()) # Approximate fallback

    def truncate_for_slm(self, text: str, max_tokens: int) -> str:
        """
        Truncates text to ensure it fits within SLM context window.
        Uses precise SentencePiece tokenization if available.
        """
        if not text:
            return ""
            
        if self.sp_processor:
            ids = self.sp_processor.encode(text)
            if len(ids) <= max_tokens:
                return text
            # Truncate IDs and decode back
            truncated_ids = ids[:max_tokens]
            return self.sp_processor.decode(truncated_ids)
        
        # Fallback: Simple word truncation
        words = text.split()
        if len(words) > max_tokens:
            return " ".join(words[:max_tokens])
        return text

def get_tokenizer():
    return SakhiTokenizer()
