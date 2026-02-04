
import os
import sys
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Verify environment variables
supabase_url = os.getenv("SUPABASE_URL")
if not supabase_url:
    print("Error: SUPABASE_URL not found in .env")
    sys.exit(1)

# Import the RAG function from its new location
try:
    from modules.search_hierarchical import hierarchical_rag_query, format_hierarchical_context
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def run_debug():
    query = "What is the cost of IVF?"
    print(f"Querying: '{query}'")
    
    try:
        results, best_sim = hierarchical_rag_query(query)
        print(f"\nFound {len(results)} results (Best Similarity: {best_sim})")
        
        context = format_hierarchical_context(results)
        
        with open("rag_debug_log.txt", "w", encoding="utf-8") as f:
            f.write(f"Query: {query}\n\n")
            f.write(f"Raw Results: {results}\n\n")  # ADDED DEBUGGING
            f.write(f"Found {len(results)} results (Best Similarity: {best_sim})\n\n")
            f.write("--- GENERATED CONTEXT ---\n")
            f.write(context)
            f.write("\n-------------------------\n")
            
            # CHECK DIRECT DB CONTENT
            try:
                from supabase_client import supabase_select
                print("Fetching FAQ ID 44 directly from sakhi_faq...")
                row = supabase_select("sakhi_faq", filters="id=eq.44")
                f.write(f"\n\n--- DIRECT DB FETCH (ID: 44) ---\n{row}\n")
            except Exception as e:
                f.write(f"\n\n--- DIRECT DB FETCH FAILED ---\n{e}\n")

            # Check for currency symbols
            if "$" in context:
                f.write("\n[!] Found '$' symbol in context. Source data has dollars.\n")
            elif "₹" in context or "Rs" in context or "INR" in context:
                f.write("\n[+] Found Rupee symbols/mentions in context.\n")
            else:
                f.write("\n[?] No currency symbols found in context.\n")
        
        print("Results written to rag_debug_log.txt")
            
    except Exception as e:
        print(f"Error running query: {e}")

if __name__ == "__main__":
    run_debug()
