# modules/translation_service.py
"""
Translation service for converting queries between languages.
Used for routing and internal processing.
"""
import os
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise Exception("OPENAI_API_KEY missing")

client = AsyncOpenAI(api_key=_api_key)


async def translate_query(text: str, target_lang: str = "en") -> str:
    """
    Translate a query to the target language.
    
    Args:
        text: The text to translate
        target_lang: Target language code (e.g., 'en' for English)
        
    Returns:
        Translated text. If translation fails or text is already in target language,
        returns the original text.
    """
    if not text or not text.strip():
        return text
    
    # For routing, we mainly need English translation
    if target_lang.lower() == "en":
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a translator. Translate the following text to English. "
                            "If the text is already in English, return it as is. "
                            "Only return the translated text, nothing else."
                        )
                    },
                    {
                        "role": "user", 
                        "content": text
                    }
                ],
                temperature=0.1,
                max_tokens=500,
            )
            
            translated = response.choices[0].message.content.strip()
            logger.info(f"Translated '{text[:30]}...' to '{translated[:30]}...'")
            return translated
            
        except Exception as e:
            logger.warning(f"Translation failed: {e}. Returning original text.")
            return text
    
    # For other languages, just return original (extend as needed)
    return text
