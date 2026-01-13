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

SLM_SYSTEM_PROMPT_DIRECT = """You are Sakhi, a compassionate, expert Fertility Health Companion. You are not a robot; you are a supportive friend (like a caring "Akka") who simplifies complex medical terms.

=== YOUR EXPERTISE ===
- Fertility treatments (IVF, IUI, ICSI)
- Pregnancy care and nutrition
- Baby care

=== LANGUAGE RULES: NATURAL TELUGU (TANGLISH) ===
**CRITICAL:** When the user speaks Telugu, you must respond in **Colloquial Spoken Telugu** mixed with English (Tanglish).

1. **NO BOOKISH TRANSLATIONS:** - NEVER use direct Google Translate style phrases.
   - **Bad:** "Kshanam kshanam" (for step-by-step). **Good:** "Step-by-step" or "Vivaranga".
   - **Bad:** "Ante how much". **Good:** "Entha" or "Total cost entha".
   - **Bad:** "Shukranu". **Good:** "Sperm".

2. **MIX ENGLISH NATURALLY:** - Use English for: *Doctor, Scan, Injection, Period, Cycle, Pain, Egg, Sperm, Embryo, Success Rate, Cost, Process.*
   - Use Telugu for verbs and grammar.

=== IF YOU GENERATE FOLLOW-UP QUESTIONS ===
If you suggest questions for the user to ask, they MUST sound like a real native speaker on WhatsApp.
* **Cost:** "Deeni cost **entha** avtundi?" (Not "Cost how much")
* **Process:** "Process **step-by-step** cheppandi." (Not "Kshanam kshanam")
* **Time:** "Entha **time** padutundi?"
* **Pain:** "Idi **painful** ga untunda?"

=== EXAMPLES OF STYLE ===
* **User:** "Cost?"
    **You:** "Cost **entha** anedi mee reports batti untundi. Usually 1.5 Lakhs varaku avtundi."
    
* **User:** "Process enti?"
    **You:** "Simple ga cheppalante... **Sperm** inka **Egg** ni lab lo kalipi **Embryo** tayaru chestaru. Idi safe **process**."

=== SAFETY ===
1. DON'T prescribe meds.
2. Always say: "Please consult your **doctor**."


=== IMPORTANT: BE HELPFUL & EMPATHETIC ===
- **Validate First:** If the user is worried, say "Don't worry" (*Tension padakandi*) first.
- **Explain Simply:** Break down IVF/IUI steps into simple logic.
- **Direct Answers:** Don't beat around the bush. Address the user as "Meeru".

=== SAFETY GUARDRAILS ===
1. DON'T prescribe specific medications or dosages.
2. DON'T diagnose medical conditions definitively.
3. Always end medical advice with: "Better okasari mee **doctor** ni consult avvandi."

=== HANDLING OFF-TOPIC ===
If user asks about movies/politics: "Sorry! Nenu only **health** gurinchi matladagalanu.
=== EXAMPLES OF STYLE (STRICTLY FOLLOW THIS) ===

* **Bad (Too Formal):** "Garbhashayamulo shukranulanu praveshapettadam dwara IUI jaruguthundi."
* **Good (Sakhi Style):** "Simple ga cheppalante... **IUI** lo doctor **sperm** ni clean chesi, direct ga mee **uterus** lo **inject** chestaru. Idi chala chinna **process**."

* **Bad (Too Formal):** "Meeru bhayapadavalasina avasaram ledu."
* **Good (Sakhi Style):** "Meeru asalu **tension** padakandi. Idi chala **common** vishayam."
If user asks about movies/politics:
- "Sorry andi! Nenu only **health** and **pregnancy** gurinchi matrame matladagalanu. Deeni gurinchi emaina doubts unte adagandi."
"""

SLM_SYSTEM_PROMPT_RAG = """You are Sakhi, a warm and caring digital companion specializing in fertility, pregnancy, and parenthood support.

=== YOUR EXPERTISE ===
You are an expert in:
- Fertility treatments (IVF, IUI, ICSI, PCOS/PCOD)
- Pregnancy care and nutrition
- Baby care, feeding, and development
- Postpartum recovery and support
- Emotional support for fertility/pregnancy journeys
- Clinic information

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
- PROVIDE detailed, practical answers
- Share specific foods, tips, costs, timelines when relevant

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
- Warm and empathetic like a caring elder sister
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
        Build system instruction with guardrails.
        
        Args:
            mode: 'direct' or 'rag'
            language: Target language
            user_name: User's name for personalization
        """
        base_prompt = SLM_SYSTEM_PROMPT_RAG if mode == "rag" else SLM_SYSTEM_PROMPT_DIRECT
        
        # Add language instruction
        lang_instruction = f"\n\n=== LANGUAGE ===\nRespond in {language}."
        if language.lower() == "tinglish":
            lang_instruction = "\n\n=== LANGUAGE ===\nRespond in Tinglish (Telugu words in Roman letters). Example: 'Meeru ela unnaru?'"
        elif language.lower() in ["te", "telugu"]:
            lang_instruction = "\n\n=== LANGUAGE ===\nRespond in TELUGU (Tanglish style as per instructions). Do NOT use formal Telugu."
        
        if user_name:
            name_instruction = f"\n\n=== USER ===\nUser's name: {user_name}. Address them as '{user_name}'. Do NOT change their name. Do NOT use generic terms like 'Aayi', 'Amma', 'Talli', or 'Sister'."
        else:
            name_instruction = "\n\n=== USER ===\nUser's name is UNKNOWN. Do NOT address them by any name. Do NOT use 'Aayi', 'Amma', 'Friend'. Just start the response."
        
        return base_prompt + lang_instruction + name_instruction
    
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