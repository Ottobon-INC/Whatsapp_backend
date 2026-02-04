import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Telugu grammatical markers (NOT just words)
TELUGU_GRAMMAR_MARKERS = (
    "emaina", "enti", "ela", "enduku",
    "ni", "ki", "lo", "ga",
    "undi", "ledu", "untaya",
    "chestunda", "emina", 
    "chestha", "chesthundha", "cheyali", "vellali", "entha",
    "gurinchi", "meeru", "nenu", "maaku", "naaku",
    "ante", "avunu", "kaadu", "inka", "kuda",
    "chesaru", "chestaru", "cheyandi", "untundi", "untaru",
    "cheppandi", "telusukovalani", "anukuntunnara","namaste","namaskaram"
)

# Common English words that indicate English language
ENGLISH_COMMON_WORDS = {
    # Question words
    "what", "which", "why", "how", "when", "where", "who",
    # Verbs
    "is", "are", "am", "was", "were", "do", "does", "did", "can", "should", "will", "would", "could",
    "have", "has", "had", "be", "been", "being",
    "explain", "tell", "describe", "show", "give", "help", "understand",
    # Common words
    "the", "a", "an", "to", "for", "of", "in", "on", "at", "with", "about", "from",
    "me", "my", "you", "your", "it", "its", "this", "that", "these", "those",
    # Greetings
    "hello", "hi", "hey", "thanks", "thank", "please", "sorry", "ok", "okay",
    "good", "morning", "evening", "night", "bye", "goodbye",
    # Medical English
    "doctor", "treatment", "symptoms", "cost", "process", "test", "report",
}

def has_telugu_unicode(text: str) -> bool:
    return any(0x0C00 <= ord(c) <= 0x0C7F for c in text)

def transliterate_to_telugu(text: str) -> str:
    return transliterate(text, sanscript.ITRANS, sanscript.TELUGU)

def telugu_density(text: str) -> float:
    telugu_chars = sum(1 for c in text if 0x0C00 <= ord(c) <= 0x0C7F)
    return telugu_chars / max(len(text), 1)

def has_telugu_grammar(words) -> bool:
    """Check if any Telugu grammar markers are present."""
    return any(w in TELUGU_GRAMMAR_MARKERS for w in words)

def count_english_words(words) -> int:
    """Count English common words in the input."""
    return sum(1 for w in words if w in ENGLISH_COMMON_WORDS)

# -------------------------
# MAIN DETECTOR
# -------------------------
def detect_language(text: str) -> str:
    """
    Detect language of user input.
    
    Returns:
        'telugu' - Telugu Unicode script
        'tinglish' - Telugu words in Roman script
        'english' - Pure English
    """
    text = text.strip()
    # Use regex to split words, ignoring punctuation
    words = re.findall(r'\b\w+\b', text.lower())
    

    if not words:
        return "english"
    # 1️⃣ Telugu script → Telugu
    if has_telugu_unicode(text):
        return "telugu"

    # 2️⃣ Count Telugu grammar markers vs English words
    telugu_marker_count = sum(1 for w in words if w in TELUGU_GRAMMAR_MARKERS)
    english_word_count = count_english_words(words)
    
    # 3️⃣ If Telugu grammar markers present and more than English words → Tinglish
    if telugu_marker_count > 0 and telugu_marker_count >= english_word_count:
        return "tinglish"
    
    # 4️⃣ If English words are dominant → English
    if english_word_count > 0:
        return "english"
    
    # 5️⃣ Check for Telugu grammar without clear English structure
    if has_telugu_grammar(words):
        return "tinglish"
    
    # 6️⃣ Default to English for unclear cases
    return "english"

