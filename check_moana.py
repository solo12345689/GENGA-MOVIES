import httpx
import asyncio
import json

async def check():
    url = "http://localhost:8080/api/search?query=Moana%202"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(check())
