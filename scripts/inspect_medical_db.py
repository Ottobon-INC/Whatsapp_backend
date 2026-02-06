
import os
import sys

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase_client import supabase_select

def inspect_db():
    print("\n--- INSPECTING MEDICAL DICTIONARY ---")
    try:
        rows = supabase_select("sakhi_medical_dictionary", select="*")
        
        if not rows:
            print("Table is EMPTY.")
            return

        print(f"Found {len(rows)} rows.")
        print("-" * 60)
        print(f"{'ID':<5} | {'Term Hash (Prefix)':<15} | {'Token Key':<15} | {'Created At'}")
        print("-" * 60)
        
        for r in rows:
            t_hash = r.get('term_hash', '')[:10] + "..."
            t_key = r.get('token_key')
            # Handle None
            t_key_str = str(t_key) if t_key else "NULL (❌)"
            
            print(f"{r['id']:<5} | {t_hash:<15} | {t_key_str:<15} | {r.get('created_at')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_db()
