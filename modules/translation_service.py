# modules/translation_service.py
import logging
from deep_translator import GoogleTranslator
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SOURCE_CACHE = {} # Simple in-memory cache to save API calls

def translate_query(text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
    """
    Translate user query to English for better RAG retrieval.
    
    Args:
        text (str): The user's input message.
        source_lang (str): Source language code ('te' for Telugu, or 'auto').
        target_lang (str): Target language (default 'en').
        
    Returns:
        str: The translated text, or original text if translation fails.
    """
    text = text.strip()
    if not text:
        return ""

    # Check Cache
    cache_key = f"{text}_{source_lang}_{target_lang}"
    if cache_key in SOURCE_CACHE:
        logger.info("Translation cache hit")
        return SOURCE_CACHE[cache_key]

    try:
        # Use simple heuristics to avoid translating English
        # If input is already English-like (ASCII only), skip
        if text.isascii() and source_lang == "auto":
             # Double check logic: Tinglish is ASCII but needs translation.
             # Only skip if we are SURE it's English. 
             # For safety in this project, we might rely on the 'detect_lang' module beforehand
             # but here we'll let the translator decide or the caller pass explicit source.
             pass

        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated_text = translator.translate(text)
        
        if translated_text:
            logger.info(f"Translated: '{text[:30]}...' -> '{translated_text[:30]}...'")
            SOURCE_CACHE[cache_key] = translated_text
            return translated_text
            
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        # Fallback: Return original text (better than nothing)
        return text

    return text
