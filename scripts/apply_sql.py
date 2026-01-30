import os
import sys

# Add parent directory to path for imports and .env loading
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import psycopg2
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"), override=True)

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or os.getenv("IGCCSVC_DB_URL")

if not DB_URL:
    print("❌ DATABASE_URL, SUPABASE_DB_URL, or IGCCSVC_DB_URL not found in .env")
    exit(1)

if len(sys.argv) > 1:
    SQL_FILE = sys.argv[1]
else:
    SQL_FILE = os.path.join(PROJECT_ROOT, "sql", "setup_leads.sql")

if not os.path.exists(SQL_FILE):
    print(f"❌ {SQL_FILE} not found")
    exit(1)

try:
    print("Connecting to database...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    with open(SQL_FILE, "r") as f:
        sql = f.read()
    
    print(f"Applying {SQL_FILE}...")
    cur.execute(sql)
    conn.commit()
    print("✅ SQL applied successfully!")
    
    cur.close()
    conn.close()

except ImportError:
    print("❌ psycopg2 not installed. Please run: pip install psycopg2-binary")
except Exception as e:
    print(f"❌ Error applying SQL: {e}")
