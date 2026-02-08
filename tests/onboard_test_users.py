import httpx
import asyncio
import json
import os

BASE_URL = "http://72.61.228.9:8000/sakhi/chat"
USERS_FILE = "tests/test_users.json"
MAX_STEPS = 5

async def onboard_user(client, phone):
    print(f"Onboarding {phone}...")
    # Initial trigger
    msg = "Hello" 
    
    for _ in range(MAX_STEPS):
        try:
            resp = await client.post(BASE_URL, json={"message": msg, "phone_number": phone})
            if resp.status_code != 200:
                print(f"  Error {resp.status_code}")
                return
            
            data = resp.json()
            mode = data.get("mode")
            reply = data.get("reply", "")
            
            if mode != "onboarding":
                print(f"  {phone} is ready! (Mode: {mode})")
                return
            
            print(f"  [Server]: {reply[:50]}...")
            
            # Decide next input based on reply
            msg = "TestUser" # Default (Name)
            if "gender" in reply.lower():
                msg = "Female"
            elif "location" in reply.lower() or "city" in reply.lower():
                msg = "Hyderabad"
                
            print(f"  [Client]: {msg}")
            
        except Exception as e:
            print(f"  Exception: {e}")
            return

async def main():
    if not os.path.exists(USERS_FILE):
        print(f"File {USERS_FILE} not found!")
        return
        
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        
    async with httpx.AsyncClient() as client:
        for user in users:
            await onboard_user(client, user)

if __name__ == "__main__":
    asyncio.run(main())
