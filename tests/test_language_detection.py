# test_language_detection.py
"""Quick test for language detection fixes."""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.detect_lang import detect_language

tests = [
    ("Hello", "english"),
    ("Explain me IUI", "english"),
    ("What is IVF", "english"),
    ("IVF ki cost enti", "tinglish"),
    ("nausea issue", "english"),
    ("hi", "english"),
    ("thanks", "english"),
    ("meeru ela unnaru", "tinglish"),
    ("IVF gurinchi cheppandi", "tinglish"),
    ("Tell me about fertility", "english"),
    ("How are you", "english"),
    ("Good morning", "english"),
    ("naaku help kavali", "tinglish"),
]

print("\n=== Language Detection Tests ===\n")
passed = 0
for text, expected in tests:
    result = detect_language(text)
    status = "✅" if result == expected else "❌"
    if result == expected:
        passed += 1
    print(f"{status} '{text}' → {result} (expected: {expected})")

print(f"\n=== {passed}/{len(tests)} Tests Passed ===\n")
