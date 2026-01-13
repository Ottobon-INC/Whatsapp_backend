import os
import re
from typing import List, Dict, Optional, Tuple, Any

from openai import OpenAI
from dotenv import load_dotenv

# Internal module imports
from modules.detect_lang import detect_language
from modules.text_utils import truncate_response
from search_hierarchical import hierarchical_rag_query, format_hierarchical_context

# Load env variables (ensure .env is loaded)
load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise Exception("OPENAI_API_KEY missing")

client = OpenAI(api_key=_api_key)

# =============================================================================
# CONSTANTS & PROMPTS
# =============================================================================

LANGUAGE_LOCK_PROMPT = """
=== ABSOLUTE LANGUAGE CONSTRAINT ===

This is a HARD RULE and OVERRIDES all context, examples, and knowledge.

If target language is TINGLISH:
- Use ONLY Roman alphabets (a–z).
- NEVER output Telugu script (Unicode 0C00–0C7F).
- Even if context contains Telugu script, DO NOT copy it.
- Internally translate and respond ONLY in Roman letters.
- Sentence structure should remain Telugu-like (e.g., "Meeru ela unnaru?").
- Do NOT switch to pure English (e.g., "How are you?" is INCORRECT).

If target language is TELUGU:
- Respond ONLY in Telugu Unicode.
- Use STRICTLY colloquial spoken Telugu (Vyavaharika).
- STRONGLY AVOID formal/bookish words (Granthika).
- Write like a friend talking, not like a Wikipedia article.
- Use simple verbs: e.g., 'cheppandi' instead of 'vivarinchandi'.
- CRITICAL: REPLACE complex/formal Telugu words with English words written in Telugu script.
    - NEVER USE: 'చలనశీలత' (Motility), 'సామర్థ్యం' (Efficiency), 'నిర్ధారణ' (Diagnosis).
    - USE INSTEAD: 'మోటిలిటీ', 'ఎఫిషియెన్సీ', 'టెస్ట్'.
    - Rule: If a word is hard to read or scientific, use the English version in Telugu script.

If target language is ENGLISH:
- Use ONLY natural English.

Before finalizing the answer:
- Verify output matches the target language.
- Rewrite if it violates this rule.

f"{name_line}\n"
        "Address the user by name when available; if the name is long, use a shorter friendly form.\n"
        "Maintain continuity using the conversation history.\n"
        "For safety: suggest consulting a doctor for personalized medical advice.\n"

=== END LANGUAGE CONSTRAINT ===
"""

CLASSIFIER_SYS_PROMPT = """
You are a routing assistant.
Your job is to classify the user's message intent into specific signals.

Signals:
1. "MEDICAL": User is asking about IVF, pregnancy, periods, fertility, symptoms, costs, or medical procedures.
2. "SMALLTALK": User is greeting (Hi, Hello), asking "How are you?", or general chat.
3. "OUT_OF_SCOPE": User is asking about unrelated topics (Cricket, Movies, Politics).

Return ONLY a JSON object:
{"signal": "MEDICAL" | "SMALLTALK" | "OUT_OF_SCOPE"}
"""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def contains_telugu_unicode(text: str) -> bool:
    """
    Check if text contains any characters in the Telugu Unicode block (0x0C00 - 0x0C7F).
    """
    return any(0x0C00 <= ord(c) <= 0x0C7F for c in text)

def is_mostly_english(text: str) -> bool:
    """
    Check if text is predominantly English using common stopwords.
    Returns True if English stopwords appear frequently.
    """
    english_stopwords = {"the", "is", "and", "of", "to", "in", "it", "that", "for", "with", "are", "on", "as", "at", "be", "this", "have", "from"}
    words = text.lower().replace(".", " ").replace(",", " ").split()
    if not words:
        return False
        
    english_count = sum(1 for w in words if w in english_stopwords)
    ratio = english_count / len(words)
    
    # If more than 15% of words are core English stopwords, it's likely English sentences.
    # Tinglish might have 'is' or 'and' but rarely 'the', 'of', 'for' in valid grammatical positions.
    return ratio > 0.15

def force_rewrite_to_tinglish(text: str, user_name: Optional[str] = None) -> str:
    """
    Forcefully rewrite text into Tinglish (Roman script).
    Handles both Telugu script and Pure English input.
    """
    print(f"DEBUG: Rewriting text: '{text[:50]}...' with user_name: '{user_name}'")
    system_prompt = (
        "You are a strict translation and transliteration engine.\n"
        "Your goal is to convert the input text into 'Tinglish' (Telugu spoken in Roman English letters).\n"
        "RULES:\n"
        "1. If input is English -> Translate to colloquial Telugu and write in Roman script.\n"
        "2. If input is Telugu script -> Transliterate to Roman script.\n"
        "3. Keep the meaning exact but make it sound like a natural Telugu speaker chat.\n"
        "4. Output ONLY the Romanized text.\n"
        "5. Example: 'How are you?' -> 'Meeru ela unnaru?'\n"
        "6. Example: 'నమస్కారం' -> 'Namaskaram'.\n"
        "7. Do NOT add filler words like 'Aam', 'Mmm', 'Avunu' unless in the source.\n"
        "8. Do NOT invent a name if none is in the input.\n"
    )

    if user_name and user_name.strip():
         system_prompt += f"9. The user's name is '{user_name}'. Address them by this name. Do NOT change it.\n"
    else:
         system_prompt += "9. The user's name is UNKNOWN. Do NOT use any name or title (like Ma'am/Sir/Aayi). Just start the sentence.\n"

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=1024
        )
        out_text = completion.choices[0].message.content.strip()
        
        # NUCLEAR OPTION: Regex remove "Aam", "Aayi"
        # Matches "Aam," "Aam " at start, or anywhere.
        import re
        out_text = re.sub(r'(?i)\b(aam|aayi|avunu)\b[,.]*', '', out_text).strip()
        
        return out_text
    except Exception as e:
        print(f"Error re-writing Tinglish: {e}")
        return text

def _friendly_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    trimmed = name.strip()
    if not trimmed:
        return None
    lowered = trimmed.lower()
    if lowered in {"null", "none", "user", "test", "unknown"}:
        return None
    # shorten if very long
    parts = trimmed.split()
    candidate = parts[0]
    if len(candidate) > 14:
        candidate = candidate[:14]
    return candidate

def _build_history_block(history: Optional[List[Dict[str, str]]]) -> str:
    if not history:
        return ""
    
    block = "\n=== CONVERSATION HISTORY ===\n"
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        block += f"{role.upper()}: {content}\n"
    block += "=== END HISTORY ===\n"
    return block

# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================

def classify_message(message: str) -> Dict[str, Any]:
    """
    1. Deterministically detect language.
    2. Use LLM to detect signal (intent).
    Returns: {"language": str, "signal": str}
    """
    # 1. Single source of truth for language
    detected_lang = detect_language(message)
    
    # 2. Detect Signal via LLM
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CLASSIFIER_SYS_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0.0, # Deterministic classification
            response_format={"type": "json_object"}
        )
        import json
        data = json.loads(completion.choices[0].message.content)
        signal = data.get("signal", "SMALLTALK")
    except Exception as e:
        print(f"Classification error: {e}")
        signal = "SMALLTALK" # Fail safe

    return {
        "language": detected_lang,
        "signal": signal
    }

def generate_smalltalk_response(
    prompt: str,
    target_lang: str,
    history: Optional[List[Dict[str, str]]],
    user_name: Optional[str] = None,
) -> str:
    
    history_block = _build_history_block(history)
    
    system_content = (
        f"{LANGUAGE_LOCK_PROMPT}\n"
        f"TARGET LANGUAGE: {target_lang.upper()}\n\n"
        "You are Sakhi, a warm, emotional South Indian companion.\n"
        "The user is engaging in casual chat (Smalltalk).\n"
        "Be friendly, empathetic, and polite. Do NOT give medical advice here.\n"
        "Keep responses concise and natural.\n"
        f"USER NAME: {user_name}\n"
        "INSTRUCTION: Address the user by name if provided. NEVER use 'Aayi'.\n"
        f"{history_block}"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        response_text = completion.choices[0].message.content.strip()
        
        # Truncate
        response_text = truncate_response(response_text)

        # HARD ENFORCEMENT: Tinglish check
        if target_lang.lower() == "tinglish":
            if contains_telugu_unicode(response_text) or is_mostly_english(response_text):
                 response_text = force_rewrite_to_tinglish(response_text, user_name=user_name)
            
        return response_text

    except Exception as e:
        print(f"Smalltalk gen error: {e}")
        return "I am sorry, I am having trouble thinking right now."

def generate_medical_response(
    prompt: str,
    target_lang: str,
    history: Optional[List[Dict[str, str]]],
    user_name: Optional[str] = None,
) -> Tuple[str, List[dict]]:
    
    # 1. RAG Retrieval
    kb_results = hierarchical_rag_query(prompt)
    context_text = format_hierarchical_context(kb_results)

    user_name = _friendly_name(user_name)
    name_line = f"User name: {user_name}" if user_name else "User name: Not provided"
    has_history = bool(history)
    history_block = _build_history_block(history)

    # 2. Construct System Prompt
    system_content = (
        f"{LANGUAGE_LOCK_PROMPT}\n"
        f"TARGET LANGUAGE: {target_lang.upper()}\n\n"
        "You are Sakhi, a medical support chatbot for IVF and fertility.\n"
        "Use the retrieved context below to answer accurate medical questions.\n"
        "\n"
        "=== RETRIEVED CONTEXT ===\n"
        "Disclaimer: Context may be in Telugu or English. Use it for meaning, NOT for direct copying.\n"
        f"{context_text}\n"
        "=== END CONTEXT ===\n"
        "\n"
        "RESPONSE RULES:\n"
        "1. Prioritize context facts. If answer is not in context, use general safe medical knowledge.\n"
        "2. Add a standard disclaimer about consulting a doctor for specific advice.\n"
        "3. FORMATTING (Strict):\n"
        "   - Main helpful response (Paragraphs or bullet points).\n"
        "   - Add '\\n\\n' (Double Newline).\n"
        "   - Write ' Follow ups : ' (Note the leading space).\n"
        "   - Add '\\n' (Single Newline).\n"
        "   - 3 context-aware follow-up questions from the next line.\n"
        "   - CRITICAL: Do NOT use '**Follow-up**' or 'Follow Up:' or ANY other variation. Use EXACTLY ' Follow ups : '.\n"
        f"{name_line}\n"
        "Address the user by name when available; if the name is long, use a shorter friendly form.\n"
        "Maintain continuity using the conversation history.\n"
        "For safety: suggest consulting a doctor for personalized medical advice.\n"
        f"{history_block}"
    )

    # 3. LLM Generation
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4, 
        )
        response_text = completion.choices[0].message.content.strip()
        
        # Truncate
        response_text = truncate_response(response_text)
        
        # HARD ENFORCEMENT: Tinglish check
        if target_lang.lower() == "tinglish":
            if contains_telugu_unicode(response_text) or is_mostly_english(response_text):
                 response_text = force_rewrite_to_tinglish(response_text, user_name=user_name)
            
        return response_text, kb_results

    except Exception as e:
        print(f"Medical gen error: {e}")
        return "I encountered an error processing your medical query.", []
