
import asyncio
import os
import sys

# Add parent directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.slm_client import get_slm_client, SLM_INTENT_PROMPT

async def test_intent_generation():
    print("=== Testing Intent Generation ===")
    
    # 1. Initialize Client
    client = get_slm_client()
    print(f"Client initialized. Endpoint: {client.endpoint_url}")
    
    # 2. Test Cases
    test_cases = [
        {"msg": "What is IVF?", "lang": "en"},
        {"msg": "I want to freeze my eggs", "lang": "en"},
        {"msg": "Cost entha?", "lang": "Tinglish"},
    ]
    
    for case in test_cases:
        print(f"\n--- Input: '{case['msg']}' ({case['lang']}) ---")
        try:
            intent = await client.generate_intent_label(case['msg'], case['lang'])
            print(f"Generated Intent: {intent}")
            
            if client.endpoint_url:
                # Basic validation if real
                assert len(intent) > 0
                print("✅ Valid length")
            else:
                 # Verification for Mock
                 assert "Here is the info regarding" in intent
                 print("✅ Mock response pattern match")
                 
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_intent_generation())
