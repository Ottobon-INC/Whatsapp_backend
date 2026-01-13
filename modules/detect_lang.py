import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Telugu grammatical markers (NOT just words)
TELUGU_GRAMMAR_MARKERS = (
    "emaina", "enti", "ela", "enduku",
    "ni", "ki", "lo", "ga",
    "undi", "ledu", "untaya",
    "chestha", "chesthundha", "cheyali", "vellali", "entha"
)

# Minimal English structure words
ENGLISH_STOPWORDS = {
    "what", "which", "why", "how", "when", "where",
    "is", "are", "do", "does", "did", "can", "should",
    "have", "to"
}

def has_telugu_unicode(text: str) -> bool:
    return any(0x0C00 <= ord(c) <= 0x0C7F for c in text)

def transliterate_to_telugu(text: str) -> str:
    return transliterate(text, sanscript.ITRANS, sanscript.TELUGU)

def telugu_density(text: str) -> float:
    telugu_chars = sum(1 for c in text if 0x0C00 <= ord(c) <= 0x0C7F)
    return telugu_chars / max(len(text), 1)

def has_telugu_grammar(words) -> bool:
    return any(w in TELUGU_GRAMMAR_MARKERS for w in words)

def has_english_structure(words) -> bool:
    return any(w in ENGLISH_STOPWORDS for w in words)

# -------------------------
# MAIN DETECTOR
# -------------------------
def detect_language(text: str) -> str:

    text = text.strip()
    # Use regex to split words, ignoring punctuation
    words = re.findall(r'\b\w+\b', text.lower())

    # 1️⃣ Telugu script → Telugu
    if has_telugu_unicode(text):
        return "telugu"

    # 2️⃣ Telugu grammar in Latin script → Tinglish (KEY FIX)
    if has_telugu_grammar(words):
        return "tinglish"

    # 3️⃣ Clear English structure → English
    if has_english_structure(words):
        return "english"

    # 4️⃣ Fallback using transliteration
    telugu_text = transliterate_to_telugu(text)
    if telugu_density(telugu_text) > 0.6:
        # Check if it's actually English transliterated? 
        # But high density suggests Indian language logic. 
        # We'll treat as Tinglish per user logic
        return "tinglish"

    return "english"
