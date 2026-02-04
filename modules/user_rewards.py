# modules/user_rewards.py
"""
Reward Management System for Sakhi.
Awards points based on question type without affecting latency.

Reward Criteria:
- NEW_QUESTION (5 pts): Novel question not in KB (similarity < 0.4)
- MEDICAL (3 pts): Medical-related question
- FOLLOW_UP (2 pts): Follow-up from suggestions
- CONVERSATIONAL (1 pt): Basic small talk
"""
from enum import Enum
from typing import Optional
import asyncio

from supabase_client import supabase_update, supabase_insert, supabase_select


class RewardType(Enum):
    """Reward categories and their point values."""
    NEW_QUESTION = 5      # Novel question not in KB
    MEDICAL = 3           # Medical-related question
    FOLLOW_UP = 2         # Follow-up from suggestions
    CONVERSATIONAL = 1    # Basic small talk


# Similarity threshold below which a question is considered "new"
NEW_QUESTION_THRESHOLD = 0.4


def classify_for_reward(
    route: str,
    rag_similarity: Optional[float] = None,
    is_followup: bool = False
) -> RewardType:
    """
    Determine reward type based on query classification.
    
    REWARD LOGIC:
    ┌─────────────────────────────────────────────────────────────────┐
    │  5 pts  │  NEW_QUESTION   │  Any RAG route + similarity < 0.4  │
    │  3 pts  │  MEDICAL        │  SLM_RAG or OPENAI_RAG + sim ≥ 0.4 │
    │  2 pts  │  FOLLOW_UP      │  User selected a suggested question│
    │  1 pt   │  CONVERSATIONAL │  SLM_DIRECT (greetings, small talk)│
    └─────────────────────────────────────────────────────────────────┘
    
    Args:
        route: The routing decision ('slm_direct', 'slm_rag', 'openai_rag')
        rag_similarity: Best similarity score from RAG (0-1), None if no RAG
        is_followup: Whether user clicked a follow-up suggestion
        
    Returns:
        RewardType enum indicating the reward category
    """
    # Priority 1: Follow-up question (user engaged with suggestions)
    if is_followup:
        return RewardType.FOLLOW_UP  # 2 pts
    
    # Priority 2: Conversational / Small talk (no RAG route)
    if route == "slm_direct":
        return RewardType.CONVERSATIONAL  # 1 pt
    
    # Priority 3: Medical routes (SLM_RAG or OPENAI_RAG)
    if route in ("slm_rag", "openai_rag"):
        # Check if this is a NEW question (not in knowledge base)
        if rag_similarity is not None and rag_similarity < NEW_QUESTION_THRESHOLD:
            return RewardType.NEW_QUESTION  # 5 pts
        else:
            return RewardType.MEDICAL  # 3 pts
    
    # Default fallback (shouldn't reach here)
    return RewardType.CONVERSATIONAL  # 1 pt


async def award_points(user_id: str, reward_type: RewardType) -> None:
    """
    Add reward points to user's total. Runs asynchronously.
    
    Args:
        user_id: The user's unique identifier
        reward_type: The type of reward to award
    """
    try:
        points = reward_type.value
        
        # Fetch current rewards
        rows = supabase_select(
            "sakhi_users",
            select="rewards",
            filters=f"user_id=eq.{user_id}"
        )
        
        current_rewards = 0
        if rows and isinstance(rows, list) and len(rows) > 0:
            current_rewards = rows[0].get("rewards") or 0
        
        new_total = current_rewards + points
        
        # Update the rewards
        match = f"user_id=eq.{user_id}"
        supabase_update("sakhi_users", match, {"rewards": new_total})
        
        print(f"🏆 Awarded {points} points ({reward_type.name}) to user {user_id}. New total: {new_total}")
        
    except Exception as e:
        # Log but don't fail the main request
        print(f"⚠️ Failed to award points: {e}")


async def store_new_question(user_id: str, question: str, similarity: float) -> None:
    """
    Store novel questions for future KB expansion.
    
    Args:
        user_id: The user's unique identifier
        question: The question text
        similarity: The similarity score that triggered NEW_QUESTION
    """
    try:
        payload = {
            "user_id": user_id,
            "question": question,
            "similarity_score": similarity
        }
        supabase_insert("sakhi_new_questions", payload)
        print(f"📝 Stored new question for KB expansion: '{question[:50]}...' (similarity: {similarity:.2f})")
        
    except Exception as e:
        # Log but don't fail the main request
        print(f"⚠️ Failed to store new question: {e}")


def get_user_rewards(user_id: str) -> int:
    """
    Fetch current reward total for user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        Total reward points (0 if not found)
    """
    try:
        rows = supabase_select(
            "sakhi_users",
            select="rewards",
            filters=f"user_id=eq.{user_id}"
        )
        
        if rows and isinstance(rows, list) and len(rows) > 0:
            return rows[0].get("rewards") or 0
        return 0
        
    except Exception as e:
        print(f"⚠️ Failed to fetch rewards: {e}")
        return 0
