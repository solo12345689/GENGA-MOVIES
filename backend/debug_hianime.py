import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        try:
            print("Testing /api/anime/home...")
            # We need to find the actual port. Let's try 8000.
            res = await client.get("http://127.0.0.1:8000/api/anime/home")
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
