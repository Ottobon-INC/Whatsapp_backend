import logging
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid redundant API calls
# Key: "text_source_target", Value: "translated_text"
SOURCE_CACHE = {}

def translate_query(text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
    """
    Translates the input query to English using Google Translate (deep-translator).
    This is used to improve RAG retrieval accuracy.
    """
    if not text:
        return ""

    # 1. Check Cache
    cache_key = f"{text}_{source_lang}_{target_lang}"
    if cache_key in SOURCE_CACHE:
        logger.info(f"Translation cache hit: '{text}' -> '{SOURCE_CACHE[cache_key]}'")
        return SOURCE_CACHE[cache_key]

    try:
        # 2. Perform Translation
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated_text = translator.translate(text)
        
        # 3. Save to Cache
        if translated_text:
            SOURCE_CACHE[cache_key] = translated_text
            logger.info(f"Translated: '{text}' -> '{translated_text}'")
            return translated_text
        
        return text

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        # Fail safe: return original text so the bot doesn't crash
        return text
