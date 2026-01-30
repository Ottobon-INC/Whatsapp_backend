"""Test script to debug the 500 error"""
import asyncio
import traceback
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_chat():
    from main import sakhi_chat, ChatRequest
    
    # Use an existing phone number that's fully onboarded
    req = ChatRequest(
        phone_number='9876543210',  # Change to your test phone number
        message='what is the cost of ivf in vizag',
        language='en'
    )
    
    try:
        result = await sakhi_chat(req)
        print('\n=== SUCCESS ===')
        # Safe print for Windows console
        try:
            print(json.dumps(result, indent=2, ensure_ascii=True))
        except:
            print(f"Route: {result.get('route')}")
            print(f"Mode: {result.get('mode')}")
            print(f"Language: {result.get('language')}")
            print(f"Reply length: {len(result.get('reply', ''))}")
            print("(Full reply contains special characters)")
    except Exception as e:
        print('\n=== ERROR ===')
        print(f'Error type: {type(e).__name__}')
        print(f'Error message: {str(e)}')
        print('\n=== FULL TRACEBACK ===')
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting test...")
    asyncio.run(test_chat())
    print("\nTest complete.")
