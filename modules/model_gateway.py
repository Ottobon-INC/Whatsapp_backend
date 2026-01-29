# modules/model_gateway.py
import logging
from enum import Enum
from typing import List, Dict, Union
import numpy as np

from rag import generate_embedding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Route(Enum):
    """Routing destinations for user queries."""
    SLM_DIRECT = "slm_direct"  # Small talk, no RAG needed
    SLM_RAG = "slm_rag"  # Simple medical, RAG + SLM
    OPENAI_RAG = "openai_rag"  # Complex medical, RAG + OpenAI


class ModelGateway:
    """
    Semantic router that directs user queries to appropriate model endpoints
    based on vector similarity to predefined anchor categories.
    """
    
    # Anchor examples for each category
    SMALL_TALK_EXAMPLES = [
        "hi",
        "hello",
        "hey there",
        "hey",
        "thanks",
        "thank you",
        "thanks a lot",
        "thank you so much",
        "who are you",
        "what is your name",
        "may i know your name",
        "how are you",
        "how are you doing",
        "how's it going",
        "what's up",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
        "bye",
        "goodbye",
        "see you",
        "see you later",
        "talk to you later",
        "nice to meet you",
        "pleased to meet you",
        "ok",
        "okay",
        "cool",
        "great",
        "awesome",
        "no problem",
        "you're welcome",
        "welcome",
    ]
    
    MEDICAL_SIMPLE_EXAMPLES = {
        "IVF": [
            "what is ivf",
            "how ivf treatment works",
            "ivf success rate",
            "ivf process step by step",
            "ivf treatment cost",
            "is ivf painful",
            "ivf risks",
            "who needs ivf",
        ],
        "IUI": [
            "what is iui",
            "iui treatment process",
            "iui success rate",
            "difference between iui and ivf",
            "iui cost",
            "is iui painful",
        ],
        "ICSI": [
            "what is icsi",
            "icsi vs ivf",
            "when is icsi needed",
            "icsi success rate",
            "icsi treatment steps",
        ],
        "FERTILITY": [
            "what is fertility",
            "how to improve fertility naturally",
            "fertility age limit",
            "fertility tests for women",
            "fertility tests for men",
        ],
        "FEMALE_INFERTILITY": [
            "what causes female infertility",
            "female infertility symptoms",
            "tests for female infertility",
            "can female infertility be treated",
        ],
        "MALE_INFERTILITY": [
            "what causes male infertility",
            "male infertility symptoms",
            "sperm count test",
            "how to improve sperm quality",
        ],
        "LAPAROSCOPY": [
            "what is laparoscopy",
            "laparoscopy for infertility",
            "is laparoscopy surgery painful",
            "recovery time after laparoscopy",
        ],
        "POSTPARTUM": [
            "what is postpartum period",
            "postpartum recovery tips",
            "postpartum depression symptoms",
            "diet after delivery",
        ],
        "CONCEPTION": [
            "what is conception",
            "how conception happens",
            "best time for conception",
            "how long does conception take",
        ],
        "EMBRYO_FREEZING": [
            "what is embryo freezing",
            "why embryo freezing is done",
            "how long embryos can be frozen",
            "is embryo freezing safe",
        ],
        "SPERM_FREEZING": [
            "what is sperm freezing",
            "how sperm freezing works",
            "how long sperm can be frozen",
            "who should freeze sperm",
        ],
        "EGG_FREEZING": [
            "what is egg freezing",
            "best age for egg freezing",
            "egg freezing process",
            "egg freezing success rate",
        ],
        "PCOS": [
            "what is pcos",
            "pcos symptoms",
            "pcos treatment",
            "pcos diet plan",
            "can pcos cause infertility",
        ],
        "PCOD": [
            "what is pcod",
            "pcod symptoms",
            "pcod vs pcos",
            "pcod treatment",
        ],
        "AYURVEDA_TREATMENTS": [
            "ayurveda treatment for infertility",
            "ayurvedic remedies for pcos",
            "is ayurveda safe for fertility",
            "ayurveda diet for pregnancy",
        ],
        "HYSTEROSCOPY": [
            "what is hysteroscopy",
            "why hysteroscopy is done",
            "hysteroscopy recovery time",
            "is hysteroscopy painful",
        ],
        "PREGNANCY": [
            "early pregnancy symptoms",
            "pregnancy diet tips",
            "safe exercises during pregnancy",
            "pregnancy tests accuracy",
        ],
        "SURROGACY": [
            "what is surrogacy",
            "surrogacy process",
            "who needs surrogacy",
            "is surrogacy legal in india",
        ],
        "C_SECTION": [
            "what is c section",
            "recovery after c section",
            "c section vs normal delivery",
            "when c section is needed",
        ],
        "NATURAL_BIRTH": [
            "what is natural birth",
            "benefits of normal delivery",
            "pain relief for natural birth",
            "preparing for natural delivery",
        ],
        "NUTRITION_AND_TESTS": [
            "nutrition needed for ivf",
            "fertility blood tests",
            "hormone tests for pregnancy",
            "vitamins needed for conception",
        ],
        "MEDICATION_AND_EXERCISES": [
            "fertility medicines for women",
            "medicines to improve sperm count",
            "exercises for fertility",
            "yoga for pregnancy",
        ],
        "TREATMENTS_GENERAL": [
            "what treatments are available",
            "what are the treatments",
            "available treatments",
            "types of treatments",
            "treatment options",
            "fertility treatment options",
            "what treatment should i take",
            "which treatment is best",
            "list of treatments",
            "treatments for infertility",
            "treatments have",
            "what treatments do you have",
            "tell me about treatments",
            "explain treatments",
        ],
    }
    
    MEDICAL_COMPLEX_EXAMPLES = [
        "severe bleeding",
        "baby not moving",
        "sharp abdominal pain",
        "emergency symptoms",
        "heavy bleeding in pregnancy",
        "sudden severe headache",
        "vision problems pregnancy",
        "chest pain difficulty breathing",
        "preeclampsia symptoms",
        "miscarriage signs",
    ]
    
    FACILITY_INFO_EXAMPLES = [
        "what is the phone number for vijayawada branch",
        "address of hyderabad clinic",
        "where is your office located",
        "contact number for the clinic",
        "how can I reach the xyz branch",
        "clinic timings",
        "where are you located",
        "phone number for appointment",
        "address for fertility center",
        "branch locations",
        "where are the clinics in vizag",
        "vizag clinic address",
        "visakhapatnam branch location",
        "show me clinics near me",
        "clinic contact details",
        "where can I find your clinic",
        "nearest clinic location",
        "fertility center address",
        "branch office contact",
        "how to reach the clinic",
    ]
    
    # Similarity thresholds for routing decisions
    SMALL_TALK_THRESHOLD = 0.75  # High confidence needed for small talk
    MEDICAL_SIMPLE_THRESHOLD = 0.60  # Moderate confidence for simple medical
    FACILITY_INFO_THRESHOLD = 0.50  # Lower threshold for facility/location queries to catch more
    
    def __init__(self):
        """Initialize the gateway by computing anchor vectors."""
        logger.info("Initializing ModelGateway with anchor vectors...")
        
        # Compute mean anchor vectors for each category
        self.small_talk_anchor = self._compute_mean_vector(self.SMALL_TALK_EXAMPLES)
        self.medical_simple_anchor = self._compute_mean_vector(self.MEDICAL_SIMPLE_EXAMPLES)
        self.medical_complex_anchor = self._compute_mean_vector(self.MEDICAL_COMPLEX_EXAMPLES)
        self.facility_info_anchor = self._compute_mean_vector(self.FACILITY_INFO_EXAMPLES)
        
        logger.info("ModelGateway initialized successfully")
    
    def _compute_mean_vector(self, examples) -> np.ndarray:
        """
        Compute the mean embedding vector for a list of example texts.
        
        Args:
            examples: List of example texts OR dict with category -> list of examples
            
        Returns:
            Mean embedding vector as numpy array
        """
        # Handle dictionary input (flatten all values)
        if isinstance(examples, dict):
            flat_examples = []
            for category_examples in examples.values():
                flat_examples.extend(category_examples)
            examples = flat_examples
        
        embeddings = [generate_embedding(example) for example in examples]
        mean_vector = np.mean(embeddings, axis=0)
        return mean_vector
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def decide_route(self, user_text: str) -> Route:
        """
        Determine the appropriate route for a user query based on semantic similarity.
        
        Args:
            user_text: User's input message
            
        Returns:
            Route enum indicating which model to use
        """
        # Generate embedding for user input
        user_vector = np.array(generate_embedding(user_text))
        
        # Calculate similarities to each anchor
        small_talk_sim = self._cosine_similarity(user_vector, self.small_talk_anchor)
        medical_simple_sim = self._cosine_similarity(user_vector, self.medical_simple_anchor)
        medical_complex_sim = self._cosine_similarity(user_vector, self.medical_complex_anchor)
        facility_info_sim = self._cosine_similarity(user_vector, self.facility_info_anchor)
        
        # Log similarity scores for debugging
        logger.info(f"Query: '{user_text[:50]}...'")
        logger.info(f"Similarity scores - Small Talk: {small_talk_sim:.3f}, "
                   f"Medical Simple: {medical_simple_sim:.3f}, "
                   f"Medical Complex: {medical_complex_sim:.3f}, "
                   f"Facility Info: {facility_info_sim:.3f}")
        
        # Find the maximum medical similarity
        max_medical_sim = max(medical_simple_sim, medical_complex_sim)
        
        # Routing logic:
        # 1. Small talk gets priority if it's above threshold OR if it's clearly the highest
        if small_talk_sim >= self.SMALL_TALK_THRESHOLD:
            logger.info(f"→ Routing to: SLM_DIRECT (small talk above threshold)")
            return Route.SLM_DIRECT
        
        # 2. Even below threshold, if small talk is highest by a margin, use it
        #    This catches "Hello" (0.705) vs medical (0.2)
        if small_talk_sim > max_medical_sim + 0.3:
            logger.info(f"→ Routing to: SLM_DIRECT (small talk clearly highest)")
            return Route.SLM_DIRECT
        
        # 3. Check for facility/location queries
        if facility_info_sim >= self.FACILITY_INFO_THRESHOLD:
            logger.info(f"→ Routing to: SLM_RAG (facility/location info query)")
            return Route.SLM_RAG
        
        # 4. Medical routing
        if medical_complex_sim >= medical_simple_sim and medical_complex_sim >= 0.35:
            logger.info(f"→ Routing to: OPENAI_RAG (complex medical detected)")
            return Route.OPENAI_RAG
        
        if medical_simple_sim >= self.MEDICAL_SIMPLE_THRESHOLD:
            logger.info(f"→ Routing to: SLM_RAG (simple medical query)")
            return Route.SLM_RAG
        
        # 5. Default to OpenAI for safety when confidence is low
        logger.info(f"→ Routing to: OPENAI_RAG (low confidence, defaulting to safe option)")
        return Route.OPENAI_RAG


# Module-level singleton instance
_gateway_instance = None


def get_model_gateway() -> ModelGateway:
    """
    Get or create a singleton ModelGateway instance.
    
    Returns:
        ModelGateway instance
    """
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = ModelGateway()
    return _gateway_instance
