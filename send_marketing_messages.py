# send_marketing_messages.py
"""
Marketing message automation script.
Fetches users from sakhi_users table and sends WhatsApp marketing messages
via the local middleware running on port 3000.
"""

import argparse
import time
import requests

from supabase_client import supabase_select


# ========== CONFIGURATION ==========
MIDDLEWARE_URL = "http://localhost:3000/v1/send-message"
INTERNAL_SECRET = "my_super_secret_key_123"
DEFAULT_LANGUAGE_CODE = "en_IN"
RATE_LIMIT_DELAY_SECONDS = 1  # Delay between requests to avoid flooding


def fetch_users(role_filter: str = "USER", limit: int = None):
    """
    Fetch users from sakhi_users table.
    
    Args:
        role_filter: Filter by role (e.g., 'USER'). Set to None to fetch all.
        limit: Maximum number of users to fetch.
    
    Returns:
        List of user dictionaries.
    """
    filters = ""
    if role_filter:
        filters = f"role=eq.{role_filter}"
    
    users = supabase_select("sakhi_users", select="user_id,name,phone_number", filters=filters, limit=limit)
    return users or []


def send_marketing_message(
    phone_number: str,
    template_name: str,
    user_name: str = None,
    language_code: str = DEFAULT_LANGUAGE_CODE,
) -> dict:
    """
    Send a marketing message to a single user via the middleware.
    
    Args:
        phone_number: User's phone number (without country code).
        template_name: Name of the approved Meta template.
        user_name: User's name to substitute in template variable {{1}}.
        language_code: Language code for the template.
    
    Returns:
        Response from the middleware as a dictionary.
    """
    # Format phone number with country code
    formatted_phone = f"91{phone_number}"
    
    payload = {
        "phone": formatted_phone,
        "template_name": template_name,
        "language_code": language_code,
    }
    
    # Add template variables if user_name is provided
    # The middleware expects 'body_parameters' array for template placeholders
    if user_name:
        payload["body_parameters_named"] = {"name": user_name}  # ✅ Named
    
    headers = {
        "x-internal-secret": INTERNAL_SECRET,
        "Content-Type": "application/json",
    }
    
    response = requests.post(MIDDLEWARE_URL, json=payload, headers=headers, timeout=30)
    return {
        "status_code": response.status_code,
        "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
    }


def run_campaign(template_name: str, limit: int = None, dry_run: bool = False):
    """
    Run a marketing campaign by sending messages to all eligible users.
    
    Args:
        template_name: Name of the approved Meta template.
        limit: Maximum number of users to process.
        dry_run: If True, only print what would be sent without actually sending.
    """
    print(f"📢 Starting Marketing Campaign")
    print(f"   Template: {template_name}")
    print(f"   Limit: {limit or 'None (all users)'}")
    print(f"   Dry Run: {dry_run}")
    print("-" * 50)
    
    users = fetch_users(role_filter="USER", limit=limit)
    
    if not users:
        print("❌ No users found to send messages to.")
        return
    
    print(f"✅ Found {len(users)} user(s) to message.\n")
    
    success_count = 0
    fail_count = 0
    
    for i, user in enumerate(users, 1):
        phone = user.get("phone_number")
        name = user.get("name") or "User"
        
        if not phone:
            print(f"[{i}/{len(users)}] ⚠️  Skipping {name}: No phone number.")
            fail_count += 1
            continue
        
        if dry_run:
            print(f"[{i}/{len(users)}] 🔍 [DRY RUN] Would send to {name} ({phone})")
            success_count += 1
        else:
            try:
                result = send_marketing_message(phone, template_name, user_name=name)
                if result["status_code"] == 200:
                    print(f"[{i}/{len(users)}] ✅ Sent to {name} ({phone})")
                    success_count += 1
                else:
                    print(f"[{i}/{len(users)}] ❌ Failed for {name} ({phone}): {result}")
                    fail_count += 1
            except requests.RequestException as e:
                print(f"[{i}/{len(users)}] ❌ Error for {name} ({phone}): {e}")
                fail_count += 1
            
            # Rate limiting
            if i < len(users):
                time.sleep(RATE_LIMIT_DELAY_SECONDS)
    
    print("-" * 50)
    print(f"📊 Campaign Summary:")
    print(f"   Total Users: {len(users)}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {fail_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send marketing messages to users.")
    parser.add_argument("template_name", help="Name of the approved Meta template to send.")
    parser.add_argument("--limit", type=int, default=None, help="Max number of users to message.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending messages.")
    
    args = parser.parse_args()
    
    run_campaign(
        template_name=args.template_name,
        limit=args.limit,
        dry_run=args.dry_run,
    )
