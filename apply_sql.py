import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")

if not DB_URL:
    print("❌ DATABASE_URL or SUPABASE_DB_URL not found in .env")
    exit(1)

SQL_FILE = "setup_leads.sql"

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
