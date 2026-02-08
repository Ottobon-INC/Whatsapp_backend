import httpx
import asyncio

BASE_URL = "http://72.61.228.9:8000/sakhi/chat"
USER_PHONE = "8143630515"

async def check_state():
    async with httpx.AsyncClient() as client:
        payload = {
            "message": "Hello",
            "phone_number": USER_PHONE
        }
        resp = await client.post(BASE_URL, json=payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Mode: {data.get('mode')}")
            print(f"Reply: {data.get('reply')}")
        else:
            print(resp.text)

if __name__ == "__main__":
    asyncio.run(check_state())
