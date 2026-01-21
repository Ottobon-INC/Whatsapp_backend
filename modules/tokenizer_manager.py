# modules/tokenizer_manager.py
import tiktoken
import logging
import os
import sentencepiece as spm
from typing import List, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
GPT_MODEL_NAME = "gpt-4o"
DEFAULT_SLM_MODEL_PATH = "modules/assets/telugu.model" 

class SakhiTokenizer:
    """
    Centralized Tokenizer Manager for Hybrid Architecture.
    
    1. GPT-4o Tokenizer (tiktoken) -> For routing and complex queries.
    2. SLM Tokenizer (SentencePiece) -> For cost-effective Telugu-native processing.
    """
    
    def __init__(self, slm_model_path: str = None):
        """
        Initialize both tokenizers.
        """
        self.tiktoken_encoding = tiktoken.encoding_for_model(GPT_MODEL_NAME)
        self.sp_processor = None
        
        # Initialize SentencePiece for SLM
        model_path = slm_model_path or os.getenv("SLM_TOKENIZER_PATH", DEFAULT_SLM_MODEL_PATH)
        
        if os.path.exists(model_path):
            try:
                self.sp_processor = spm.SentencePieceProcessor(model_file=model_path)
                logger.info(f"SLM Tokenizer loaded from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load SLM Tokenizer: {e}")
        else:
            logger.warning(f"SLM Tokenizer model not found at {model_path}. Running without specialized Telugu tokenization.")

    def encode_for_gpt(self, text: str) -> List[int]:
        """
        Encode text using OpenAI's tokenizer (cl100k_base).
        Returns list of token IDs.
        """
        return self.tiktoken_encoding.encode(text)

    def count_tokens_gpt(self, text: str) -> int:
        """
        Count tokens for OpenAI pricing/context checks.
        """
        return len(self.encode_for_gpt(text))

    def encode_for_slm(self, text: str) -> List[str]:
        """
        Encode text using SentencePiece (Unigram) for SLM.
        Returns list of string tokens (subwords).
        """
        if self.sp_processor:
            return self.sp_processor.encode(text, out_type=str)
        
        # Fallback: Simple whitespace split + basic English subwording behavior emulation
        # This is a very rough fallback!
        return text.split()

    def count_tokens_slm(self, text: str) -> int:
        """
        Count tokens for SLM context checks.
        """
        if self.sp_processor:
            return len(self.sp_processor.encode(text))
        
        # Fallback approximation for Telugu/English mixed
        # A rough estimate: chars / 4
        return len(text) // 4

    def truncate_for_slm(self, text: str, max_tokens: int = 1024) -> str:
        """
        Truncate text to fit SLM context window, preserving Telugu subwords.
        """
        if self.sp_processor:
            ids = self.sp_processor.encode(text)
            if len(ids) <= max_tokens:
                return text
            
            truncated_ids = ids[:max_tokens]
            return self.sp_processor.decode(truncated_ids)
        
        # Fallback truncation
        return text[:max_tokens * 4]  # Approx chars

# Singleton Instance
_tokenizer_instance = None

def get_tokenizer() -> SakhiTokenizer:
    global _tokenizer_instance
    if _tokenizer_instance is None:
        _tokenizer_instance = SakhiTokenizer()
    return _tokenizer_instance
