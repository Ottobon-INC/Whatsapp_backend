import asyncio
import time
import httpx
import statistics
import json
import random
import os

# Configuration
BASE_URL = "http://72.61.228.9:8000/sakhi/chat" # Target URL provided by user
TIMEOUT_SECONDS = 120.0 # Increased timeout for load
USERS_FILE = "tests/test_users.json"

QUESTIONS = [
    "What should I eat during the first trimester of pregnancy?",
    "Is it safe to travel by air during pregnancy?",
    "How much weight should I expect to gain during pregnancy?",
    "What are the early signs of labor?",
    "Can I drink coffee while pregnant?",
    "What is the difference between IVF and IUI?",
    "How can I relieve morning sickness naturally?",
    "Is it normal to have swelling in my feet during pregnancy?",
    "What vitamins are essential for prenatal care?",
    "How do I know if my baby is latching correctly during breastfeeding?",
    "What are the risks of gestational diabetes?",
    "When should I start feeling the baby move?",
    "Is it safe to exercise during pregnancy?",
    "What foods should I avoid while breastfeeding?",
    "How long does it take to recover from a C-section?"
]

def get_test_users():
    """Reads users from JSON file."""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users = json.load(f)
                print(f"Loaded {len(users)} users from {USERS_FILE}")
                return users
    except Exception as e:
        print(f"Warning: Could not read {USERS_FILE}: {e}")
    return []

async def send_chat_request(client, i, phone_number, question):
    payload = {
        "message": question,
        "phone_number": phone_number
    }
    start = time.time()
    try:
        response = await client.post(BASE_URL, json=payload)
        duration = time.time() - start
        
        # Check if request was successful
        if response.status_code == 200:
            status = "SUCCESS"
            # Try to parse JSON to ensure valid response
            try:
                data = response.json()
                # Optional: check if 'reply' key exists
                if "reply" not in data:
                    status = "INVALID_JSON"
            except:
                status = "INVALID_JSON"
        else:
            status = f"FAIL_{response.status_code}"
            
        print(f"Req {i:02d} (User {phone_number}): {status} in {duration:.2f}s")
        return {
            "id": i,
            "status": status,
            "duration": duration,
            "code": response.status_code,
            "question": question
        }
            
    except httpx.RequestError as e:
        duration = time.time() - start
        print(f"Req {i:02d} (User {phone_number}): ERROR {e} in {duration:.2f}s")
        return {
            "id": i,
            "status": "ERROR",
            "duration": duration,
            "error": str(e),
            "question": question
        }
    except Exception as e:
        duration = time.time() - start
        print(f"Req {i:02d} (User {phone_number}): EXCEPTION {e} in {duration:.2f}s")
        return {
            "id": i,
            "status": "EXCEPTION",
            "duration": duration,
            "error": str(e),
            "question": question
        }

async def main():
    print(f"Starting load test on {BASE_URL}")
    
    users = get_test_users()
    if not users:
        print("No users found in tests/test_users.json")
        return

    # Ensure we don't have more questions than users or vice-versa
    num_requests = min(len(users), len(QUESTIONS))
    users = users[:num_requests]
    
    print(f"Concurrency: {num_requests}")
    print("-" * 40)
    
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        # Create tasks - pairing unique user with unique question
        tasks = [send_chat_request(client, i, users[i], QUESTIONS[i]) for i in range(num_requests)]
        
        # Run concurrently
        start_total = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_total
        
    print("-" * 40)
    print("Load Test Completed")
    
    # Analysis
    successful = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] != "SUCCESS"]
    
    success_count = len(successful)
    fail_count = len(failed)
    
    print(f"Total Requests: {num_requests}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total Wall Time: {total_time:.2f}s")
    
    if successful:
        durations = [r["duration"] for r in successful]
        min_time = min(durations)
        max_time = max(durations)
        avg_time = statistics.mean(durations)
        median_time = statistics.median(durations)
        
        print(f"\nResponse Time Metrics (Successful Requests):")
        print(f"  Min: {min_time:.2f}s")
        print(f"  Max: {max_time:.2f}s")
        print(f"  Avg: {avg_time:.2f}s")
        print(f"  Median: {median_time:.2f}s")
        
        # Requests per second (roughly)
        rps = success_count / total_time
        print(f"\nThroughput: {rps:.2f} req/s")
        
    if failed:
        print("\nFailure Details:")
        for r in failed[:10]: # Print first 10 failures
            print(f"  Req {r['id']}: {r.get('status')} - {r.get('error', 'Unknown code')}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more.")

if __name__ == "__main__":
    asyncio.run(main())
