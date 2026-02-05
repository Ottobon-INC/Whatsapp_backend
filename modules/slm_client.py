
# modules/slm_client.py
import logging
import os
from typing import Optional, List, Dict
import httpx
from fastapi import HTTPException

from modules.text_utils import truncate_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# LEVEL 2: SLM PROMPT GUARDRAILS
# ============================================================================

SLM_LANGUAGE_LOCK = """
=== ABSOLUTE LANGUAGE CONSTRAINT ===
If target language is TINGLISH:
- Use ONLY Roman alphabets (a–z).
- NEVER output Telugu script (Unicode 0C00–0C7F).
- Sentence structure should remain Telugu-like (e.g., "Meeru ela unnaru?").
- Do NOT switch to pure English.

If target language is TELUGU:
- Respond ONLY in Telugu Unicode.
- Use STRICTLY colloquial spoken Telugu.

If target language is ENGLISH:
- Use ONLY natural English.
"""





SLM_INTENT_PROMPT = """
You are a helpful assistant.
Task: Summarize the user's query into a single short sentence (max 1 sentence).
This sentence should act as a header or topic summary for the answer.

Examples:
Input: "What is IVF?"
Output: "Here is the information about IVF."

Input: "EE age lo pregnancy better?"
Output: "Pregnancy ee age lo try chesthey better."

Input: "Cost entha?"
Output: "Here are the cost details."

RULES:
1. MAX 1 sentence.
2. Output in the requested TARGET LANGUAGE.
3. Be direct and polite.
"""

SLM_SYSTEM_PROMPT_DIRECT = f"""{SLM_LANGUAGE_LOCK}
You are Sakhi, a friendly AI assistant.

=== TASK: GREETINGS ONLY ===
User is saying "Hi", "Hello", "Namaste" or "How are you".
You must reply with a simple, standard greeting.

=== STRICT VOCABULARY (TINGLISH) ===
Use ONLY these exact phrases. Do NOT create new sentences.
1. Greeting: "Hi [Name], ela unnaru?"
2. I am good: "Nenu bagunnanu, thanks! Meeru ela unnaru?"
3. Good Morning: "Good morning! Ee roju meeku manchiga undali."
4. Asking help: "Meeku health doubts emaina unnaya?"
5. Namaste: "Namaste [Name]! meeku elanti help kavali?"

=== BANNED WORDS ===
- NEVER say "okaru", "vellanu", "Sakhi Sakhi".
- NEVER say "I am very one" or nonsense.

=== EXAMPLES ===

User: namaste
Target: TINGLISH
Bot: Namaste [Name]! meeku elanti help kavali?

User: Meeru ela unnaru?
Target: TINGLISH
Bot: Nenu bagunnanu, thanks! Meeru ela unnaru?

=== HANDLING OFF-TOPIC ===
If user asks about movies/politics/sports:
- "Sorry, I can only help with health and pregnancy questions."
"""

SLM_SYSTEM_PROMPT_RAG = f"""{SLM_LANGUAGE_LOCK}

You are Sakhi, a warm and caring digital companion specializing in fertility, pregnancy, and parenthood support.

=== YOUR EXPERTISE ===
You are an expert in:
- Fertility treatments (IVF, IUI, ICSI, PCOS/PCOD)
- Pregnancy care and nutrition
- Baby care, feeding, and development
- Postpartum recovery and support
- Emotional support for fertility/pregnancy journeys
- Clinic information

=== FORMATTING RULES (Strict) ===
1. Use Hyphens (- ) for bullet points. Do NOT use * for bullets.
2. Use Single Asterisks (*text*) for bolding. Do NOT use **text**.
3. Structure for Lists: - *Topic*: Description

=== HOW TO USE KNOWLEDGE (RAG + General Knowledge) ===
You will receive RETRIEVED CONTEXT from our knowledge base. Follow this priority:

1. **FIRST: Use Retrieved Context**
   - If the context contains relevant information, USE IT as your primary source
   - Quote facts, figures, and specifics from the context
   - This is trusted, verified information

2. **SECOND: Fill Gaps with General Knowledge**
   - If the context does NOT cover the user's question (or is incomplete)
   - Use your general medical/health knowledge to provide helpful information
   - This ensures users always get a useful answer

3. **BE TRANSPARENT (optional)**
   - You may indicate when providing general guidance vs specific knowledge
   - Example: "Generally speaking..." or "Based on typical cases..."

=== IMPORTANT: ALWAYS BE HELPFUL ===
- NEVER refuse to answer on-topic health questions
- NEVER say "I don't have that information" - provide general guidance instead
- Provide detailed, practical answers
- Share specific foods, tips, costs, timelines when relevant

=== CURRENCY / COSTS ===
- ALWAYS use Indian Rupees (₹) or INR for costs.
- If the context only has Dollar ($) amounts, explicitly state: "These are international estimates; prices in India may vary."
- Do NOT output $ symbol without explanation.

=== SAFETY GUARDRAILS (Only for risky situations) ===
1. DON'T prescribe specific medications or dosages
2. DON'T diagnose medical conditions definitively
3. For emergencies, advise IMMEDIATE medical attention
4. For complex cases, suggest consulting a doctor

=== HANDLING OFF-TOPIC QUESTIONS ===
If user asks about sports, movies, politics, celebrities, etc.:
- Respond warmly - don't make user feel bad
- Explain your focus is on fertility and pregnancy
- Offer to help with health-related topics

=== YOUR PERSONALITY ===
- Warm and empathetic like a caring friend
- Helpful and informative (not overly cautious)
- Uses simple language and emojis appropriately
- Addresses user by name when provided
"""


class SLMClient:
    """
    Client for interacting with a Small Language Model (SLM).
    
    Includes Level 2 Prompt Guardrails for safety and quality.
    
    To enable real SLM:
    1. Set environment variable: SLM_ENDPOINT_URL
    2. Optionally set: SLM_API_KEY, SLM_MODEL_NAME
    3. Replace mock methods with actual HTTP calls (using httpx or similar)
    """
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize SLM client.
        
        Args:
            endpoint_url: SLM API endpoint (e.g., Groq, vLLM server)
            api_key: API key for authentication
            model_name: Model identifier
        """
        self.endpoint_url = endpoint_url or os.getenv("SLM_ENDPOINT_URL")
        self.api_key = api_key or os.getenv("SLM_API_KEY")
        self.model_name = model_name or os.getenv("SLM_MODEL_NAME", "default-slm")
        
        if self.endpoint_url:
            logger.info(f"SLMClient initialized with endpoint: {self.endpoint_url}")
        else:
            logger.warning("SLMClient running in MOCK mode (no endpoint configured)")
    
    def _build_system_instruction(self, mode: str, language: str, user_name: Optional[str]) -> str:
        """
        Build system instruction with guardrails, mirroring OpenAI prompt builder.
        
        Args:
            mode: 'direct' or 'rag'
            language: Target language
            user_name: User's name for personalization
        """
        
        # 1. Handle Name Block
        safe_name = user_name.strip() if user_name else None
        if safe_name and safe_name.lower() in ["null", "none", "user", "test", "unknown"]:
             safe_name = None
             
        name_block = (
            f"USER NAME: {safe_name}\nGreeting Instruction: Start response with 'Hi {safe_name},'.\n"
            if safe_name
            else
            "USER NAME: NONE\n"
            "CRITICAL: Do NOT use any name, title, or filler word.\n"
            "DO NOT start the response with 'Aayi', 'Avunu', or any interjection.\n"
        )

        # 2. Select Base Prompt
        if mode == "rag":
            # For RAG, we construct the full prompt similarly to generate_medical_response
            system_content = (
                f"{SLM_SYSTEM_PROMPT_RAG}\n"
                f"TARGET LANGUAGE: {language.upper()}\n"
                f"{name_block}"
            )
        else:
            # For Direct/Smalltalk
            system_content = (
                f"{SLM_SYSTEM_PROMPT_DIRECT}\n"
                f"TARGET LANGUAGE: {language.upper()}\n"
                f"{name_block}"
            )
            
        return system_content
    
    async def generate_chat(
        self,
        message: str,
        language: str = "en",
        user_name: Optional[str] = None,
    ) -> str:
        """
        Generate a direct chat response (no RAG context).
        
        Args:
            message: User's message
            language: Target language for response
            user_name: User's name for personalization
            
        Returns:
            Generated response text
        """
        logger.info(f"SLM generate_chat called - Message: '{message[:50]}...', Language: {language}")
        
        if self.endpoint_url:
            # Real API call to SLM endpoint
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Build system instruction with guardrails
                    system_instruction = self._build_system_instruction("direct", language, user_name)
                    
                    # Prepare request payload matching SLM API format
                    # We inject the specific persona instructions again in the payload to ensure adherence
                    final_question = f"""
                    {system_instruction}
                    
                    USER MESSAGE:
                    {message}
                    """

                    payload = {
                        "question": final_question,  # SLM expects "question" not "message"
                        "chat_history": "",   # Empty for direct chat
                    }
                    
                    # Prepare headers
                    headers = {"Content-Type": "application/json"}
                    if self.api_key and self.api_key != "your-api-key-if-needed":
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    logger.info(f"Sending request to SLM endpoint: {self.endpoint_url}")
                    
                    response = await client.post(
                        self.endpoint_url,
                        json=payload,
                        headers=headers,
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # Extract response text (SLM returns {"reply": "..."})
                    if isinstance(result, dict):
                        response_text = result.get("reply") or result.get("response") or result.get("text") or result.get("message") or str(result)
                    else:
                        response_text = str(result)
                    
                    # Truncate response to maximum 1024 characters
                    response_text = truncate_response(response_text)
                    
                    logger.info(f"SLM response received: {response_text[:100]}...")
                    return response_text
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"SLM API error: {e.response.status_code} - {e.response.text}")
                raise HTTPException(status_code=502, detail=f"SLM API error: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.error("SLM API timeout")
                raise HTTPException(status_code=504, detail="SLM API timeout")
            except Exception as e:
                logger.error(f"Error calling SLM API: {e}")
                raise HTTPException(status_code=500, detail=f"Error calling SLM: {str(e)}")
        
        # Mock implementation (fallback if no endpoint)
        greeting = f"Hi {user_name}! " if user_name else "Hi! "
        mock_response = (
            f"{greeting} (Mock Response) Meeru adigina '{message}' gurinchi simple ga cheppalante... "
            f"Manam **IVF** process lo doctors help teesukovachu. Meeru **tension** padakandi. [Language: {language}]"
        )
        
        # Truncate response to maximum 1024 characters
        mock_response = truncate_response(mock_response)
        
        logger.info(f"SLM mock response: {mock_response[:100]}...")
        return mock_response
    
    async def generate_rag_response(
        self,
        context: str,
        message: str,
        language: str = "en",
        user_name: Optional[str] = None,
    ) -> str:
        """
        Generate a RAG-enhanced response using retrieved context.
        
        Args:
            context: Retrieved context from RAG search
            message: User's message
            language: Target language for response
            user_name: User's name for personalization
            
        Returns:
            Generated response text incorporating the context
        """
        logger.info(f"SLM generate_rag_response called - Message: '{message[:50]}...', Language: {language}")
        logger.info(f"Context length: {len(context)} characters")
        
        if self.endpoint_url:
            # Real API call to SLM endpoint for RAG
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Build system instruction with guardrails
                    system_instruction = self._build_system_instruction("rag", language, user_name)
                    
                    final_question = f"""
                    {system_instruction}
                    
                    CONTEXT INFORMATION:
                    {context}
                    
                    USER MESSAGE:
                    {message}
                    """
                    
                    payload = {
                        "question": final_question,
                        "chat_history": "",
                    }
                    
                    # Prepare headers
                    headers = {"Content-Type": "application/json"}
                    if self.api_key and self.api_key != "your-api-key-if-needed":
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    logger.info(f"Sending RAG request to SLM endpoint: {self.endpoint_url}")
                    
                    response = await client.post(
                        self.endpoint_url,
                        json=payload,
                        headers=headers,
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # Extract response text (SLM returns {"reply": "..."})
                    if isinstance(result, dict):
                        response_text = result.get("reply") or result.get("response") or result.get("text") or result.get("message") or str(result)
                    else:
                        response_text = str(result)
                    
                    # Truncate response to maximum 1024 characters
                    response_text = truncate_response(response_text)
                    
                    logger.info(f"SLM RAG response received: {response_text[:100]}...")
                    return response_text
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"SLM API error: {e.response.status_code} - {e.response.text}")
                raise HTTPException(status_code=502, detail=f"SLM API error: {e.response.status_code}")
            except httpx.TimeoutException:
                logger.error("SLM API timeout")
                raise HTTPException(status_code=504, detail="SLM API timeout")
            except Exception as e:
                logger.error(f"Error calling SLM API: {e}")
                raise HTTPException(status_code=500, detail=f"Error calling SLM: {str(e)}")
        
        # Mock implementation (fallback if no endpoint)
        greeting = f"Hello {user_name}, " if user_name else "Hello, "
        mock_response = (
            f"{greeting} (Mock RAG) Meeru adigina '{message}' gurinchi info dorikindi. "
            f"General ga **success rate** bagane untundi. [Language: {language}]"
        )
        
        # Truncate response to maximum 1024 characters
        mock_response = truncate_response(mock_response)
        
        logger.info(f"SLM mock RAG response: {mock_response[:100]}...")
        return mock_response
    
    def is_mock(self) -> bool:
        """
        Check if client is running in mock mode.
        
        Returns:
            True if no endpoint configured (mock mode), False otherwise
        """
        return self.endpoint_url is None

    async def generate_intent_label(
        self,
        message: str,
        language: str = "en",
    ) -> str:
        """
        Generate a short intent label/summary for the user's message.
        
        Args:
            message: User's message
            language: Target language
            
        Returns:
            Short intent sentence (max 1 sentence)
        """
        logger.info(f"SLM generate_intent_label called - Message: '{message[:30]}...'")
        
        if self.endpoint_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Construct prompt
                    system_instruction = f"{SLM_INTENT_PROMPT}\nTARGET LANGUAGE: {language.upper()}"
                    
                    final_question = f"""
                    {system_instruction}
                    
                    USER MESSAGE:
                    {message}
                    """
                    
                    payload = {
                        "question": final_question,
                        "chat_history": "",
                    }
                    
                    headers = {"Content-Type": "application/json"}
                    if self.api_key and self.api_key != "your-api-key-if-needed":
                        headers["Authorization"] = f"Bearer {self.api_key}"
                        
                    response = await client.post(
                        self.endpoint_url,
                        json=payload,
                        headers=headers,
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    if isinstance(result, dict):
                        intent_text = result.get("reply") or result.get("response") or result.get("text") or str(result)
                    else:
                        intent_text = str(result)
                        
                    # CLEANUP: Remove "Follow ups" and anything after it
                    import re
                    intent_text = re.sub(r'(?i)\n\s*follow\s*-?\s*ups\s*:.*$', '', intent_text, flags=re.DOTALL).strip()
                    # Also generic "Follow up" if present
                    intent_text = re.sub(r'(?i)follow\s*-?\s*ups?.*', '', intent_text).strip()
                        
                    return intent_text.strip()
                    
            except Exception as e:
                logger.error(f"Error generating intent label: {e}")
                # Fallback to simple generic string if SLM fails
                return "Here is the information you requested."
        
        # Mock mode fallback
        return f"Here is the info regarding '{message[:20]}...'"


# Module-level singleton instance
_slm_client_instance = None


def get_slm_client() -> SLMClient:
    """
    Get or create a singleton SLMClient instance.
    
    Returns:
        SLMClient instance
    """
    global _slm_client_instance
    if _slm_client_instance is None:
        _slm_client_instance = SLMClient()
    return _slm_client_instance