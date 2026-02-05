import os
import re
from typing import List, Dict, Optional, Tuple, Any

from openai import AsyncOpenAI
from dotenv import load_dotenv

# Internal module imports
from modules.detect_lang import detect_language
from modules.text_utils import truncate_response
from modules.search_hierarchical import hierarchical_rag_query, format_hierarchical_context

# Load env variables (ensure .env is loaded)
load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise Exception("OPENAI_API_KEY missing")

client = AsyncOpenAI(api_key=_api_key)

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
- Do NOT switch to pure English.

If target language is TELUGU:
- Respond ONLY in Telugu Unicode.
- Use STRICTLY colloquial spoken Telugu.
- Avoid formal/bookish Telugu.
- Replace complex Telugu words with English words in Telugu script.

If target language is ENGLISH:
- Use ONLY natural English.

Before finalizing the answer:
- Verify output matches the target language.
- Rewrite if it violates this rule.

=== END LANGUAGE CONSTRAINT ===
"""

CLASSIFIER_SYS_PROMPT = """
You are a routing and language detection assistant.
Your job is to classify the user's message intent and detect the language.

1. Language:
- "English": Standard English.
- "Telugu": Telugu Script (e.g., మీరు ఎలా ఉన్నారు?).
- "Tinglish": Telugu spoken in English/Roman script (e.g., Meeru ela unnaru?, ivf ante enti?).
- "Hindi": Hindi.

2. Signals:
1. "MEDICAL": User is asking about IVF, pregnancy, periods, fertility, symptoms, costs, or medical procedures.
2. "SMALLTALK": User is greeting (Hi, Hello), asking "How are you?", or general chat.
3. "OUT_OF_SCOPE": User is asking about unrelated topics (Cricket, Movies, Politics).

Return ONLY a JSON object:
{"signal": "MEDICAL" | "SMALLTALK" | "OUT_OF_SCOPE", "language": "English" | "Telugu" | "Tinglish" | "Hindi"}
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

async def force_rewrite_to_tinglish(text: str, user_name: Optional[str] = None) -> str:
    """
    Forcefully rewrite text into Tinglish (Roman script).
    Splits content into Main Body and Follow-ups to process them separately.
    Enforces 'Warmth & Hope' in the main body and 'Concise Questions' in follow-ups.
    """
    import re
    
    # 1. SPLIT: Isolate Main Response and Follow-ups
    # Look for "Follow ups :" or variations case-insensitive
    split_match = re.search(r'(?i)\n\s*follow\s*-?\s*ups\s*:', text)
    
    main_body = text
    follow_ups_text = ""
    
    if split_match:
        split_idx = split_match.start()
        main_body = text[:split_idx].strip()
        follow_ups_text = text[split_idx:].strip() # Keep the header for now to identify it
        
        # Remove the header from follow_ups_text for processing
        # We will add standard header back later
        follow_ups_content = re.sub(r'(?i)^follow\s*-?\s*ups\s*:\s*', '', follow_ups_text).strip()
    else:
        follow_ups_content = ""

    # 2. PROCESS MAIN BODY (Warmth, Hope, Tinglish)
    system_prompt_body = (
        "You are 'Sakhi', a warm, empathetic, and hopeful fertility companion.\n"
        "Your task: Rewrite the input English text into *Natural Conversational Tinglish*.\n"
        "\n"
        "=== EMOTIONAL TONE: WARM & FACTUAL ===\n"
        "1. *Balance:* Be warm (like a caring friend) but *DO NOT* remove medical facts, risks, or causes.\n"
        "2. *Clarity:* If the input mentions specific conditions (e.g., 'Chromosomal abnormalities', 'Ovarian reserve'), YOU MUST INCLUDE THEM in the translation.\n"
        "3. *Empathy:* Use 'Don't worry' only *after* explaining the facts. Do not replace facts with hope.\n"
        "\n"
        "=== LANGUAGE RULES ===\n"
        "1. *Analysis:* Understand the meaning first. Don't translate word-for-word.\n"
        "2. *Sentence Structure:* Use Telugu grammar. NEVER start clauses with 'which makes' or 'due to'. Use 'Anduvalla' or ends with 'avtundi'.\n"
        "   - BAD: '...which makes conceive cheyadam hard.'\n"
        "   - GOOD: '...dani valla conceive avvadam konchem tough avtundi.'\n"
        "3. *Keep Medical Terms English:* IVF, Pregnancy, Sperm, Egg, Embryo, Doctor, Period, Success rate.\n"
        "3. *Grammar:* Use natural Telugu verb endings (untundi, avtundi, cheyali).\n"
        "4. *Vocabulary Mappings:*\n"
        "   - 'This' -> 'Ee' (e.g., 'Ee process')\n"
        "   - 'That' -> 'Adi'\n"
        "   - 'These' -> 'Ivi'\n"
        "   - 'Women' -> 'Women' or 'Aadavallalo' (NEVER use 'Ammaloki')\n"
        "   - 'Men' -> 'Magavallu' (NEVER use 'Manishi' for gender)\n"
        "   - 'Couples' -> 'Dampatulu' or 'Couples'\n"
        "   - 'Not only that' -> 'Anthe kadu' (NEVER use 'Aamathram')\n"
        "5. *Transitions:* \n"
        "   - *CRITICAL:* Do NOT use phrases like 'ivanni valla:', 'valla ki:', 'veeti valla:', or 'kaaranamga:' to introduce a list.\n"
        "   - *CORRECT:* Use a simple colon (:) or 'kinda unnavi chudandi:'. (e.g., 'Factors ivi:' or just ':')\n"
        "   - *BAD:* '...recommend chestaru, ivanni valla:' (REMOVE 'ivanni valla')\n"
        "   - *GOOD:* '...recommend chestaru:'\n"
        "6. *Phrasing Tips/Suggestions:* \n"
        "   - *CRITICAL:* When *giving* tips, NEVER say 'Konni tips ivvandi' (This means 'Give me tips'). \n"
        "   - *CORRECT:* Say 'Konni tips:' or 'Ivi konni tips:' (Here are some tips) or 'Konni tips chudandi:'.\n"
        "7. *Structure:* Use Hyphens (- ) for bullet points to avoid confusion. Format as '*Topic*: Description'. Use single asterisks (*) to make the Topic bold in WhatsApp.\n"
        "   - *CRITICAL:* Always keep the Introduction paragraph. Do not jump straight to bullets.\n"
        "8. *Corrections:*\n"
        "   - 'Outside body' -> 'Lab lo' (Better than 'External ga' or 'Body bayata')\n"
        "   - 'Assisted reproductive technology' -> 'Fertility treatment'\n"
        "\n"
        "=== EXAMPLES ===\n"
        "Input: 'IVF involves injections and is painful.'\n"
        "Output: 'IVF lo konni injections untayi, konchem discomfort undochu kani idi barinchagalige noppe. Doctor guidance to antha smooth ga avtundi.'\n"
        "\n"
        "Input: 'Success rates depend on age.'\n"
        "Output: 'Success rate anedi mee age meeda depend ayi untundi, kani correct treatment to manchi results vasthayi.'\n"
        "\n"
        "Input: 'Here are some tips:'\n"
        "Output: 'Ivi konni tips:' (NOT 'Konni tips ivvandi')\n"
    )

    if user_name and user_name.strip():
         system_prompt_body += f"9. The user's name is '{user_name}'. Address them by this name. Do NOT change it.\n"
    else:
         system_prompt_body += "9. The user's name is UNKNOWN. Do NOT use any name or title (like Ma'am/Sir/Aayi). Just start the sentence.\n"

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt_body},
                {"role": "user", "content": main_body},
            ],
            temperature=0.2,
            max_tokens=1024
        )
        rewritten_body = completion.choices[0].message.content.strip()
        
        # Regex cleanup for common hallucinations
        rewritten_body = re.sub(r'(?i)\b(aam|aayi|avunu)\b[,.]*', '', rewritten_body).strip()
        
    except Exception as e:
        print(f"Error re-writing body: {e}")
        rewritten_body = main_body


    # 3. PROCESS FOLLOW-UPS (If exist)
    rewritten_followups = ""
    if follow_ups_content:
        system_prompt_fu = (
            "You are an expert conversation designer.\n"
            "Task: Rewrite the user's specific questions into short, natural *Tinglish* questions.\n"
            "Rules:\n"
            "1. *Translate the Meaning:* Don't just pick random questions. Translate the *actual* English questions provided.\n"
            "2. *Style:* Short, punchy, spoken Telugu style (2-5 words).\n"
            "3. *Vocabulary Rules:*\n"
            "   - Use 'entha?' for cost/time (e.g., 'Cost entha?', 'Time entha?').\n"
            "   - Use 'enti?' for what/process (e.g., 'Process enti?', 'Problem enti?').\n"
            "   - Use 'untunda/untaya?' for yes/no (e.g., 'Side effects untaya?', 'Risk untunda?').\n"
            "   - Use English for nouns: Cost, Risk, Success Rate, Test, Doctor.\n"
            "   - *SIMPLIFY:* Convert complex terms like 'Chromosomal abnormalities' -> 'Risks' or 'Health issues'.\n"
            "   - *Assessment Questions:*\n"
            "     - 'What is your age?' -> 'Mee age entha?'\n"
            "     - 'How long are you trying?' -> 'Enni years nundi try chestunnaru?'\n"
            "     - 'Any health issues?' -> 'Health issues emaina unnaya?'\n"
            "4. *Prohibited:* Do not use complex words like 'prabhavitam', 'shukranu'. Keep it casual.\n"
            "5. *Grammar Check:* Ensure questions are complete sentences. (BAD: 'Cut down alcohol effects untaya?' -> GOOD: 'Alcohol tagginchadam valla effects untaya?')\n"
            "\n"
            "=== EXAMPLES ===\n"
            "Input: '1. What diets help? 2. Alternatives? 3. Success rate?'\n"
            "Output:\n"
            "1. Diet emaina follow avvala?\n"
            "2. Vere alternatives emaina unnaya?\n"
            "3. Success rate ela untundi?\n"
        )
        
        try:
            completion_fu = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt_fu},
                    {"role": "user", "content": follow_ups_content},
                ],
                temperature=0.3,
                max_tokens=200
            )
            raw_fu = completion_fu.choices[0].message.content.strip()
            
            # Formatter ensure clean list
            rewritten_followups = f"\n\n Follow ups :\n{raw_fu}"
            
        except Exception as e:
            print(f"Error re-writing follow-ups: {e}")
            rewritten_followups = f"\n\n Follow ups :\n{follow_ups_content}"

    # 4. COMBINE
    return rewritten_body + rewritten_followups

async def force_rewrite_to_telugu(text: str, user_name: Optional[str] = None) -> str:
    """
    Forcefully rewrite text into Colloquial Telugu (Telugu Script).
    Splits content into Main Body and Follow-ups to process them separately.
    Use English for complex medical terms but transliterate when possible.
    """
    import re
    
    # 1. SPLIT
    split_match = re.search(r'(?i)\n\s*follow\s*-?\s*ups\s*:', text)
    
    main_body = text
    follow_ups_text = ""
    
    if split_match:
        split_idx = split_match.start()
        main_body = text[:split_idx].strip()
        follow_ups_text = text[split_idx:].strip()
        follow_ups_content = re.sub(r'(?i)^follow\s*-?\s*ups\s*:\s*', '', follow_ups_text).strip()
    else:
        follow_ups_content = ""

    # 2. PROCESS MAIN BODY
    system_prompt_body = (
        "You are 'Sakhi', a warm, empathetic fertility companion.\n"
        "Task: Translate the input English text into *Colloquial Spoken Telugu* (Telugu Script).\n"
        "\n"
        "=== RULES ===\n"
        "1. *Script:* Use ONLY Telugu Unicode characters (ఆ, ఇ, క, గ...).\n"
        "2. *Tone:* Warm but Factual. Do NOT remove medical facts/risks. Explain them simply.\n"
        "3. *Medical Terms:* You may keep common acronyms like 'IVF', 'ICSI' in English if strictly needed, or transliterate them (ఐవిఎఫ్).\n"
        "4. *Style:* Simple spoken Telugu, not bookish.\n"
        "5. *Structure:* Use Hyphens (- ) for bullet points. Format as '*Topic*: Description'. Use single asterisks (*) for bold text in WhatsApp.\n"
        "6. *Vocabulary:* Use 'Lab lo' instead of 'Body bayata'. Use 'Magavallu' for Men (Not 'Manishi').\n"
    )

    if user_name and user_name.strip():
         system_prompt_body += f"5. Greeting: Start with 'హాయ్ {user_name},'. Do NOT translate the name (keep it if simple, or transliterate).\n"

    try:
        completion_body = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt_body},
                {"role": "user", "content": main_body},
            ],
            temperature=0.4,
            max_tokens=800
        )
        rewritten_body = completion_body.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error re-writing Telugu body: {e}")
        rewritten_body = main_body

    # 3. PROCESS FOLLOW-UPS
    rewritten_followups = ""
    if follow_ups_content:
        system_prompt_fu = (
            "You are an expert conversation designer.\n"
            "Task: Rewrite the user's questions into short, natural **Telugu** questions (Telugu Script).\n"
            "Rules:\n"
            "1. *Translate Meaning:* Translate the actual questions provided.\n"
            "2. *Style:* Short, punchy questions.\n"
            "3. *Vocabulary:* Use simple words like 'ఖర్చు ఎంత?', 'సమయం ఎంత?', 'రిస్క్ ఉందా?', 'మీ వయస్సు ఎంత?'.\n"
            "4. *Format:* Bullet points.\n"
        )
        
        try:
            completion_fu = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt_fu},
                    {"role": "user", "content": follow_ups_content},
                ],
                temperature=0.3,
                max_tokens=200
            )
            raw_fu = completion_fu.choices[0].message.content.strip()
            rewritten_followups = f"\n\n Follow ups :\n{raw_fu}"
            
        except Exception as e:
            print(f"Error re-writing Telugu follow-ups: {e}")
            rewritten_followups = f"\n\n Follow ups :\n{follow_ups_content}"

    return rewritten_body + rewritten_followups

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

async def classify_message(message: str) -> Dict[str, Any]:
    """
    1. Deterministically detect language.
    2. Use LLM to detect signal (intent).
    Returns: {"language": str, "signal": str}
    """
    
    # Default fallback
    detected_lang = detect_language(message)
    signal = "SMALLTALK"

    # Use LLM for both Signal and Language detection
    try:
        completion = await client.chat.completions.create(
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
        llm_lang = data.get("language", "")
        
        if llm_lang:
            detected_lang = llm_lang.lower()
            
            # Refinement: If LLM says "Telugu" but input has no Telugu script, it's Tinglish
            if detected_lang == "telugu" and not contains_telugu_unicode(message):
                detected_lang = "tinglish"
                
    except Exception as e:
        print(f"Classification error: {e}")
        signal = "SMALLTALK" # Fail safe

    return {
        "language": detected_lang,
        "signal": signal
    }

async def generate_smalltalk_response(
    prompt: str,
    target_lang: str,
    history: Optional[List[Dict[str, str]]],
    user_name: Optional[str] = None,
) -> str:
    
    history_block = _build_history_block(history)
    safe_name = _friendly_name(user_name)
    name_block = (
    f"USER NAME: {safe_name}\nAddress the user by this name.\n"
    if safe_name
    else
    "USER NAME: NONE\n"
    "CRITICAL: Do NOT use any name, title, or filler word.\n"
    "DO NOT start the response with 'Aam', 'Aayi', 'Avunu', or any interjection.\n"
)
    
    system_content = (
        f"{LANGUAGE_LOCK_PROMPT}\n"
        f"TARGET LANGUAGE: {target_lang.upper()}\n\n"
        "You are Sakhi, a warm, emotional South Indian companion.\n"
        "The user is engaging in casual chat.\n"
        "Be friendly but direct.\n"
        "Keep responses concise and natural.\n"
        f"{name_block}"
        f"{history_block}"
    )

    try:
        completion = await client.chat.completions.create(
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
                 response_text = await force_rewrite_to_tinglish(response_text, user_name=user_name)
            
        return response_text

    except Exception as e:
        print(f"Smalltalk gen error: {e}")
        return "I am sorry, I am having trouble thinking right now."

async def generate_medical_response(
    prompt: str,
    target_lang: str,
    history: Optional[List[Dict[str, str]]],
    user_name: Optional[str] = None,
) -> Tuple[str, List[dict]]:
    
    # 1. RAG Retrieval
    kb_results, _similarity = await hierarchical_rag_query(prompt)
    context_text = format_hierarchical_context(kb_results)
    has_history = bool(history)
    history_block = _build_history_block(history)
    safe_name = _friendly_name(user_name)

    name_block = (
        f"USER NAME: {safe_name}\nAddress the user by this name.\n"
        if safe_name
        else
        "USER NAME: NONE\n"
        "CRITICAL: Do NOT use any name, title, or filler word.\n"
        "DO NOT start with 'Aam', 'Aayi', 'Avunu', or any interjection.\n"
    )
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
        "   - Use Hyphens (- ) for bullet points. Do NOT use * for bullets.\n"
        "   - Use Single Asterisks (*text*) for bolding. Do NOT use **text**.\n"
        "   - Main helpful response (Paragraphs or lists).\n"
        "   - Add '\\n\\n' (Double Newline).\n"
        "   - Write ' Follow ups : ' (Note the leading space).\n"
        "   - Add '\\n' (Single Newline).\n"
        "   - 3 context-aware follow-up questions from the next line.\n"
        "   - CRITICAL: Do NOT use '**Follow-up**' or 'Follow Up:' or ANY other variation. Use EXACTLY ' Follow ups : '.\n"
        f"{name_block}\n"
        "Address the user by name when available; if the name is long, use a shorter friendly form.\n"
        "Maintain continuity using the conversation history.\n"
        "For safety: suggest consulting a doctor for personalized medical advice.\n"
        f"{history_block}"
    )

    # 3. LLM Generation
    try:
        completion = await client.chat.completions.create(
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
                 response_text = await force_rewrite_to_tinglish(response_text, user_name=user_name)
            
        return response_text, kb_results

    except Exception as e:
        print(f"Medical gen error: {e}")
        return "I encountered an error processing your medical query.", []