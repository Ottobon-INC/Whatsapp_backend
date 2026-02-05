import asyncio
import time
import httpx
import statistics

BASE_URL = "http://localhost:8000"
CONCURRENT_REQUESTS = 5

async def send_chat_request(i):
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "message": "Hi, how are you?",
            "phone_number": f"999999999{i}"
        }
        start = time.time()
        try:
            resp = await client.post(f"{BASE_URL}/sakhi/chat", json=payload)
            resp.raise_for_status()
            duration = time.time() - start
            print(f"Req {i}: Status {resp.status_code}, Time {duration:.2f}s")
            return duration
        except Exception as e:
            print(f"Req {i}: Failed {e}")
            return None

async def main():
    print(f"Sending {CONCURRENT_REQUESTS} concurrent requests...")
    start_total = time.time()
    tasks = [send_chat_request(i) for i in range(CONCURRENT_REQUESTS)]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_total
    
    valid_results = [r for r in results if r is not None]
    if valid_results:
        avg_time = statistics.mean(valid_results)
        print(f"\n--- Results ---")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Avg Request Time: {avg_time:.2f}s")
        print(f"Successful Requests: {len(valid_results)}/{CONCURRENT_REQUESTS}")
    else:
        print("All requests failed.")

if __name__ == "__main__":
    asyncio.run(main())
