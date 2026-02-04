# test_rewards.py
"""
Test suite for the Reward Management System.
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.user_rewards import classify_for_reward, RewardType, NEW_QUESTION_THRESHOLD


def test_classify_conversational():
    """SLM_DIRECT route should award CONVERSATIONAL (1 pt)."""
    result = classify_for_reward(route="slm_direct", rag_similarity=None)
    assert result == RewardType.CONVERSATIONAL
    assert result.value == 1
    print("✅ Conversational classification: PASS")


def test_classify_medical():
    """SLM_RAG/OPENAI_RAG with good similarity should award MEDICAL (3 pts)."""
    # Good similarity (above threshold)
    result = classify_for_reward(route="slm_rag", rag_similarity=0.6)
    assert result == RewardType.MEDICAL
    assert result.value == 3
    print("✅ Medical classification (slm_rag): PASS")
    
    result = classify_for_reward(route="openai_rag", rag_similarity=0.5)
    assert result == RewardType.MEDICAL
    assert result.value == 3
    print("✅ Medical classification (openai_rag): PASS")


def test_classify_new_question():
    """Low similarity score should award NEW_QUESTION (5 pts)."""
    # Below threshold
    result = classify_for_reward(route="slm_rag", rag_similarity=0.3)
    assert result == RewardType.NEW_QUESTION
    assert result.value == 5
    print("✅ New question classification: PASS")
    
    # Edge case: exactly at threshold
    result = classify_for_reward(route="openai_rag", rag_similarity=NEW_QUESTION_THRESHOLD - 0.01)
    assert result == RewardType.NEW_QUESTION
    print("✅ New question edge case: PASS")


def test_classify_followup():
    """Follow-up flag should take priority."""
    result = classify_for_reward(route="slm_rag", rag_similarity=0.8, is_followup=True)
    assert result == RewardType.FOLLOW_UP
    assert result.value == 2
    print("✅ Follow-up classification: PASS")


def test_reward_values():
    """Verify all reward values are correct."""
    assert RewardType.NEW_QUESTION.value == 5
    assert RewardType.MEDICAL.value == 3
    assert RewardType.FOLLOW_UP.value == 2
    assert RewardType.CONVERSATIONAL.value == 1
    print("✅ All reward values correct: PASS")


if __name__ == "__main__":
    print("\n=== Reward System Tests ===\n")
    test_classify_conversational()
    test_classify_medical()
    test_classify_new_question()
    test_classify_followup()
    test_reward_values()
    print("\n=== All Tests Passed! ===\n")
