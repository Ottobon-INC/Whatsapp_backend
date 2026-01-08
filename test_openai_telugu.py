import os
import asyncio
from dotenv import load_dotenv
from modules.response_builder import generate_medical_response

load_dotenv()

# Verify API Key
if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not found correctly.")
    exit(1)

def test_telugu(query):
    print("--- Testing OpenAI Telugu Response (Medical) ---")
    target_lang = "Telugu"
    
    print(f"User Query: {query}")
    print(f"Target Language: {target_lang}")
    print("Generating response...\n")
    
    try:
        # Mocking history as empty
        response, kb_results = generate_medical_response(
            prompt=query,
            target_lang=target_lang,
            history=[],
            user_name="Harini"
        )
        
        print("--- RESPONSE ---")
        print(response)
        print("----------------")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Enter your query (or 'q' to quit):")
    while True:
        query = input("> ")
        if query.lower() == "q":
            break
        test_telugu(query)
