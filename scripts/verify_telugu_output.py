import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from modules.response_builder import generate_medical_response

load_dotenv()

def verify():
    print("Testing Telugu Output...")
    query = "What could be stopping us from conceiving?"
    target_lang = "Tinglish"
    
    response, _ = generate_medical_response(
        prompt=query,
        target_lang=target_lang,
        history=[],
        user_name="Harini"
    )
    
    with open("verification_result.txt", "w", encoding="utf-8") as f:
        f.write(response)
    
    print("Response written to verification_result.txt")

if __name__ == "__main__":
    verify()
