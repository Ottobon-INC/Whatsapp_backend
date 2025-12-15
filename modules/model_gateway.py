# modules/model_gateway.py
import logging
from enum import Enum
from typing import List
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
        "thanks",
        "thank you",
        "who are you",
        "what is your name",
        "how are you",
        "good morning",
        "goodbye",
    ]
    
    MEDICAL_SIMPLE_EXAMPLES = [
        "what is folic acid",
        "foods for iron",
        "foods rich in calcium",
        "headache remedies",
        "how to increase hemoglobin",
        "vitamin d benefits",
        "pregnancy diet tips",
        "morning sickness relief",
        "what is ovulation",
        "safe exercises during pregnancy",
    ]
    
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
    MEDICAL_SIMPLE_THRESHOLD = 0.65  # Moderate confidence for simple medical
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
    
    def _compute_mean_vector(self, examples: List[str]) -> np.ndarray:
        """
        Compute the mean embedding vector for a list of example texts.
        
        Args:
            examples: List of example texts for a category
            
        Returns:
            Mean embedding vector as numpy array
        """
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
        
        # Routing logic based on thresholds and highest similarity
        if small_talk_sim >= self.SMALL_TALK_THRESHOLD:
            logger.info(f"→ Routing to: SLM_DIRECT (small talk detected)")
            return Route.SLM_DIRECT
        
        # Check for facility/location queries FIRST - route to SLM since it has this info
        # This takes priority over medical queries to ensure clinic info is retrieved
        if facility_info_sim >= self.FACILITY_INFO_THRESHOLD:
            logger.info(f"→ Routing to: SLM_RAG (facility/location info query)")
            return Route.SLM_RAG
        
        # Only check medical queries if it's not a facility query
        if medical_complex_sim >= medical_simple_sim:
            # Complex medical or default to safest option
            logger.info(f"→ Routing to: OPENAI_RAG (complex medical or default)")
            return Route.OPENAI_RAG
        
        if medical_simple_sim >= self.MEDICAL_SIMPLE_THRESHOLD:
            logger.info(f"→ Routing to: SLM_RAG (simple medical query)")
            return Route.SLM_RAG
        
        # Default to OpenAI for safety when confidence is low
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
