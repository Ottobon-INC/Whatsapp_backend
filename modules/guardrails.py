# modules/guardrails.py
"""
Sakhi Guardrails System - Intent-Based Scope Control
======================================================
This guardrails system focuses on:
1. Detecting user intent
2. Keeping LLM responses ON-TOPIC (fertility, pregnancy, parenthood)
3. Politely redirecting out-of-scope queries
4. NOT blocking legitimate queries - always provide helpful responses

The goal is to GUIDE the LLM, not restrict user interactions.
"""

import re
import logging
from typing import Dict, Optional, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserIntent(Enum):
    """Classified user intent categories."""
    MEDICAL_FERTILITY = "medical_fertility"      # IVF, IUI, infertility, etc.
    MEDICAL_PREGNANCY = "medical_pregnancy"      # Pregnancy symptoms, care, etc.
    MEDICAL_POSTPARTUM = "medical_postpartum"    # After delivery care
    EMOTIONAL_SUPPORT = "emotional_support"      # Stress, anxiety, feelings
    CLINIC_INFORMATION = "clinic_information"    # Clinic locations, contacts
    GREETING = "greeting"                        # Hi, hello, thanks
    OUT_OF_SCOPE = "out_of_scope"               # Sports, movies, politics, etc.
    UNCLEAR = "unclear"                          # Can't determine intent


# ============================================================================
# INTENT DETECTION
# ============================================================================

class IntentDetector:
    """
    Detects user intent to route responses appropriately.
    """
    
    # Keywords for each intent category
    FERTILITY_KEYWORDS = [
        "ivf", "iui", "icsi", "fertility", "infertility", "conceive", "conception",
        "ovulation", "egg", "sperm", "embryo", "follicle", "hormone", "fsh", "lh",
        "amh", "pcos", "pcod", "endometriosis", "blocked tube", "low sperm",
        "egg freezing", "sperm freezing", "donor", "surrogacy", "test tube",
        "fertility treatment", "trying to conceive", "ttc", "baby planning",
    ]
    
    PREGNANCY_KEYWORDS = [
        "pregnant", "pregnancy", "trimester", "week pregnant", "baby bump",
        "morning sickness", "nausea", "ultrasound", "scan", "fetal", "fetus",
        "delivery", "labor", "c-section", "normal delivery", "due date",
        "prenatal", "antenatal", "contractions", "water broke", "bleeding",
        "miscarriage", "ectopic", "preeclampsia", "gestational diabetes",
        # Nutrition during pregnancy
        "food during pregnancy", "diet during pregnancy", "pregnancy diet",
        "what to eat", "nutrition", "vitamins", "folic acid", "iron",
        "calcium", "protein", "healthy food", "pregnancy food",
    ]
    
    POSTPARTUM_KEYWORDS = [
        "postpartum", "after delivery", "breastfeeding", "lactation", "newborn",
        "baby care", "recovery after", "stitches", "c-section recovery",
        "postpartum depression", "baby blues", "milk supply",
        # Baby care and growth
        "baby", "infant", "baby growth", "baby food", "baby nutrition",
        "baby development", "baby health", "baby feeding", "formula",
        "weaning", "solid food", "baby weight", "baby milestone",
        "toddler", "child growth", "child development", "baby sleep",
        "diaper", "baby rash", "colic", "teething", "vaccination", "immunization",
    ]
    
    EMOTIONAL_KEYWORDS = [
        "stressed", "stress", "anxious", "anxiety", "worried", "scared", "fear",
        "sad", "depressed", "depression", "hopeless", "frustrated", "angry",
        "crying", "emotional", "feeling low", "cant sleep", "overwhelmed",
        "support", "help me", "dont know what to do", "confused", "lost",
        "failed", "failure", "giving up", "tired of trying",
    ]
    
    CLINIC_KEYWORDS = [
        "clinic", "hospital", "center", "location", "address", "phone",
        "contact", "appointment", "book", "visit", "doctor", "specialist",
        "timing", "hours", "near me", "branch", "vizag", "hyderabad",
        "vijayawada", "bangalore", "chennai",
    ]
    
    GREETING_KEYWORDS = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "thanks", "thank you", "bye", "goodbye", "how are you", "whats up",
        "namaste", "vanakkam",
    ]
    
    # Out of scope patterns (topics to redirect from)
    OUT_OF_SCOPE_PATTERNS = [
        # General knowledge questions (not related to health)
        r"(?i)^who is (?!my doctor|the doctor|dr\.|specialist)",  # "who is X" but not "who is my doctor"
        r"(?i)^what is the capital",
        r"(?i)^tell me about (?!ivf|iui|pregnancy|fertility|pcos|infertility)",
        
        # Sports
        r"\b(cricket|cricketer|ipl|bcci|match score|virat|kohli|dhoni|sachin|rohit sharma)\b",
        r"\b(football|soccer|fifa|messi|ronaldo|neymar|premier league)\b",
        r"\b(basketball|nba|tennis|wimbledon|olympics)\b",
        r"\b(sports?|player|team won|world cup)\b",
        
        # Entertainment
        r"\b(movie|film|cinema|actor|actress|bollywood|hollywood|netflix|webseries)\b",
        r"\b(song|singer|music|album|concert|spotify)\b",
        r"\b(shahrukh|salman|aamir|amitabh|priyanka|deepika|ranveer)\b",
        
        # Politics & News
        r"\b(politics|election|minister|government|party|modi|rahul gandhi)\b",
        r"\b(parliament|congress|bjp|vote|politician)\b",
        r"\b(news|headlines|current affairs|breaking news)\b",
        
        # Finance & Business
        r"\b(stock|share market|trading|bitcoin|crypto|sensex|nifty)\b",
        r"\b(invest|mutual fund|ipo|business news)\b",
        
        # Technology (non-health)
        r"\b(iphone|android|laptop|computer|programming|software|coding)\b",
        r"\b(facebook|instagram|twitter|tiktok|youtube)\b",
        r"\b(html|css|javascript|python|java|sql|api|database|server|cloud)\b",
        r"\b(wifi|internet|browser|4g|5g|sim card|recharge)\b",
        
        # General topics
        r"\b(recipe|cooking tips|restaurant|food review)\b",
        r"\b(weather forecast|temperature today|rain)\b",
        r"\b(game|gaming|playstation|xbox|pubg|fortnite)\b",
        r"\b(shopping|discount|sale|amazon|flipkart|offer)\b",
        r"\b(travel|vacation|hotel|flight booking|tourist)\b",
        r"\b(car|bike|automobile|vehicle)\b",
    ]
    
    @classmethod
    def detect_intent(cls, message: str) -> Tuple[UserIntent, float]:
        """
        Detect the user's intent from their message.
        
        Args:
            message: User's message
            
        Returns:
            Tuple of (UserIntent, confidence_score)
        """
        message_lower = message.lower()
        
        # Check for out of scope FIRST
        for pattern in cls.OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, message_lower):
                logger.info(f"Out of scope detected: {pattern}")
                return (UserIntent.OUT_OF_SCOPE, 0.9)
        
        # Score each intent category
        scores = {
            UserIntent.MEDICAL_FERTILITY: cls._count_keywords(message_lower, cls.FERTILITY_KEYWORDS),
            UserIntent.MEDICAL_PREGNANCY: cls._count_keywords(message_lower, cls.PREGNANCY_KEYWORDS),
            UserIntent.MEDICAL_POSTPARTUM: cls._count_keywords(message_lower, cls.POSTPARTUM_KEYWORDS),
            UserIntent.EMOTIONAL_SUPPORT: cls._count_keywords(message_lower, cls.EMOTIONAL_KEYWORDS),
            UserIntent.CLINIC_INFORMATION: cls._count_keywords(message_lower, cls.CLINIC_KEYWORDS),
            UserIntent.GREETING: cls._count_keywords(message_lower, cls.GREETING_KEYWORDS),
        }
        
        # Find highest scoring intent
        max_intent = max(scores, key=scores.get)
        max_score = scores[max_intent]
        
        if max_score == 0:
            # No keywords matched - could be a general question or unclear
            return (UserIntent.UNCLEAR, 0.3)
        
        # Normalize score (simple heuristic)
        confidence = min(max_score * 0.3, 1.0)
        
        return (max_intent, confidence)
    
    @classmethod
    def _count_keywords(cls, message: str, keywords: list) -> int:
        """Count how many keywords from the list appear in the message."""
        count = 0
        for keyword in keywords:
            if keyword in message:
                count += 1
        return count


# ============================================================================
# SCOPE GUARDRAILS (System Prompts)
# ============================================================================

class ScopeGuardrails:
    """
    System prompts that keep the LLM focused on the correct scope.
    """
    
    # Base scope definition for Sakhi
    SAKHI_SCOPE = """
=== YOUR SCOPE ===
You are Sakhi, a supportive companion for:
✓ Fertility and infertility topics (IVF, IUI, PCOS, etc.)
✓ Pregnancy care and information
✓ Postpartum and newborn care
✓ Emotional support for fertility/pregnancy journeys
✓ Clinic information and appointments

You should NOT answer questions about:
✗ Sports, movies, entertainment
✗ Politics, news, current affairs
✗ Stock market, cryptocurrency
✗ General cooking, shopping, travel
✗ Technical topics unrelated to health
"""

    # How to handle out of scope
    OUT_OF_SCOPE_HANDLING = """
=== IF USER ASKS OFF-TOPIC QUESTIONS ===
Politely redirect them back to your expertise:
- Acknowledge their question briefly
- Explain you specialize in fertility & pregnancy
- Offer to help with related topics
- Be warm and not dismissive

Example: "I appreciate you asking! While I'm not the best for [topic], I'm here to support you with fertility, pregnancy, or any health concerns. Is there anything I can help you with on your journey?"
"""

    # Medical safety (not blocking, just guiding)
    MEDICAL_GUIDANCE = """
=== MEDICAL GUIDANCE ===
- Provide helpful information from your knowledge
- Use simple, easy-to-understand language
- For specific treatments/dosages, suggest consulting a doctor
- For emergencies, recommend immediate medical attention
- Always be supportive and informative
"""

    # Emotional support guidance
    EMOTIONAL_GUIDANCE = """
=== EMOTIONAL SUPPORT ===
When user expresses difficult emotions:
- Acknowledge their feelings with empathy
- Validate that their emotions are normal
- Provide comforting words
- Suggest professional support if needed (counselor, support groups)
- Share relevant coping strategies
- Never dismiss their feelings
"""

    @classmethod
    def get_system_prompt(cls, intent: UserIntent) -> str:
        """
        Get the appropriate system prompt based on detected intent.
        
        Args:
            intent: Detected user intent
            
        Returns:
            System prompt string
        """
        base = f"""You are Sakhi, a warm and caring companion for fertility, pregnancy, and parenthood.

{cls.SAKHI_SCOPE}

{cls.MEDICAL_GUIDANCE}
"""
        
        if intent == UserIntent.OUT_OF_SCOPE:
            return base + cls.OUT_OF_SCOPE_HANDLING
        
        elif intent == UserIntent.EMOTIONAL_SUPPORT:
            return base + cls.EMOTIONAL_GUIDANCE
        
        elif intent in [UserIntent.MEDICAL_FERTILITY, UserIntent.MEDICAL_PREGNANCY, UserIntent.MEDICAL_POSTPARTUM]:
            return base + """
=== CURRENT QUERY TYPE: Medical ===
- Provide accurate, helpful medical information
- Use retrieved context if available
- Suggest consulting a doctor for personalized advice
- Be informative and supportive
"""
        
        elif intent == UserIntent.CLINIC_INFORMATION:
            return base + """
=== CURRENT QUERY TYPE: Clinic Information ===
- Provide clinic locations, contacts from your knowledge
- Help with appointment-related queries
- If unsure, suggest contacting the clinic directly
"""
        
        elif intent == UserIntent.GREETING:
            return base + """
=== CURRENT QUERY TYPE: Greeting/Small Talk ===
- Respond warmly and conversationally
- Keep Sakhi's friendly personality
- Gently offer to help with health queries
"""
        
        else:
            return base + """
=== CURRENT QUERY TYPE: General ===
- Try to relate to fertility/pregnancy if possible
- If unclear, ask clarifying questions
- Be helpful and supportive
"""
    
    @classmethod
    def get_redirect_response(cls, original_topic: str) -> str:
        """
        Get a warm, empathetic redirect response for out-of-scope queries.
        The response should be friendly so users don't feel frustrated.
        
        Args:
            original_topic: The out-of-scope topic user asked about
            
        Returns:
            Warm, empathetic redirect message
        """
        import random
        
        # Multiple warm response templates to avoid sounding robotic
        responses = [
            (
                f"Hey, I totally get it - we all have different interests! 😊\n\n"
                f"While I'm not really equipped to chat about {original_topic}, I'm here as your "
                f"friend and companion for anything related to fertility, pregnancy, or parenthood.\n\n"
                f"Is there anything on your mind about your health journey? "
                f"I'm always here to listen and help! 💜"
            ),
            (
                f"I appreciate you sharing that with me! 🌸\n\n"
                f"My expertise is really in fertility, pregnancy, and parenthood - "
                f"that's where I can truly support you best.\n\n"
                f"But I'm curious - is everything okay? Sometimes we ask random questions "
                f"when something else is on our mind. If you want to talk about anything, "
                f"health-related or just to vent about your journey, I'm here for you! 💜"
            ),
            (
                f"That's an interesting question! 😄\n\n"
                f"I wish I could help with that, but my specialty is being your supportive "
                f"companion for fertility and pregnancy matters.\n\n"
                f"If there's anything weighing on your mind - whether it's treatment questions, "
                f"emotional support, or just needing someone to listen - I'm right here. "
                f"What would you like to talk about? 💜"
            ),
        ]
        
        return random.choice(responses)


# ============================================================================
# OUTPUT CLEANUP (Light touch - don't over-process)
# ============================================================================

class OutputCleanup:
    """
    Light cleanup of LLM output - minimal changes, just remove obvious issues.
    """
    
    # Only remove these very specific AI self-references
    REMOVE_PATTERNS = [
        (r"(?i)^as an ai[,\s]", ""),
        (r"(?i)^as a language model[,\s]", ""),
        (r"(?i)\bopenai\b", ""),
        (r"(?i)\bchatgpt\b", ""),
        (r"(?i)\bgpt-4\b", ""),
    ]
    
    @classmethod
    def clean_response(cls, response: str) -> str:
        """
        Light cleanup of response - minimal changes.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Cleaned response
        """
        if not response:
            return response
        
        cleaned = response
        
        # Remove AI self-references
        for pattern, replacement in cls.REMOVE_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Fix excessive newlines
        cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)
        
        return cleaned.strip()


# ============================================================================
# MAIN GUARDRAILS CLASS
# ============================================================================

class SakhiGuardrails:
    """
    Main guardrails interface - focused on intent and scope management.
    """
    
    def __init__(self):
        self.intent_detector = IntentDetector()
        self.scope_guardrails = ScopeGuardrails()
        self.output_cleanup = OutputCleanup()
    
    def analyze_input(self, message: str) -> Dict:
        """
        Analyze user input and return intent information.
        
        Args:
            message: User's message
            
        Returns:
            Dict with intent, confidence, and system_prompt
        """
        intent, confidence = self.intent_detector.detect_intent(message)
        system_prompt = self.scope_guardrails.get_system_prompt(intent)
        
        logger.info(f"Intent detected: {intent.value} (confidence: {confidence:.2f})")
        
        return {
            "intent": intent,
            "intent_name": intent.value,
            "confidence": confidence,
            "system_prompt": system_prompt,
            "is_out_of_scope": intent == UserIntent.OUT_OF_SCOPE,
        }
    
    def get_redirect_for_out_of_scope(self, message: str) -> Optional[str]:
        """
        If message is out of scope, return a redirect response.
        Otherwise return None (let LLM handle it).
        
        Args:
            message: User's message
            
        Returns:
            Redirect response or None
        """
        intent, _ = self.intent_detector.detect_intent(message)
        
        if intent == UserIntent.OUT_OF_SCOPE:
            # Extract what they asked about
            topic = "that topic"
            for pattern in self.intent_detector.OUT_OF_SCOPE_PATTERNS:
                match = re.search(pattern, message.lower())
                if match:
                    topic = match.group(0)
                    break
            
            return self.scope_guardrails.get_redirect_response(topic)
        
        return None
    
    def clean_output(self, response: str) -> str:
        """
        Light cleanup of LLM output.
        
        Args:
            response: LLM response
            
        Returns:
            Cleaned response
        """
        return self.output_cleanup.clean_response(response)
    
    def get_system_prompt_for_intent(self, message: str) -> str:
        """
        Get the system prompt based on detected intent.
        
        Args:
            message: User's message
            
        Returns:
            System prompt string
        """
        analysis = self.analyze_input(message)
        return analysis["system_prompt"]


# Singleton instance
_guardrails_instance = None


def get_guardrails() -> SakhiGuardrails:
    """Get or create singleton guardrails instance."""
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = SakhiGuardrails()
    return _guardrails_instance


# For backward compatibility with main.py
class SafetyCategory(Enum):
    """Simple safety categories for compatibility."""
    SAFE = "safe"
    EMERGENCY = "emergency"
    SENSITIVE = "sensitive"
    OUT_OF_SCOPE = "out_of_scope"
