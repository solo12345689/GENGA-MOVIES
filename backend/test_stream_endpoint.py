import sys
import asyncio
import httpx

async def test_stream_endpoint():
    """Test the /api/stream endpoint directly"""
    
    base_url = "http://localhost:8080"
    
    # Test with a simple movie query
    test_params = {
        "mode": "url",
        "query": "Naruto",
        "content_type": "series",
        "season": "1",
        "episode": "1"
    }
    
    url = f"{base_url}/api/stream"
    
    print(f"Testing: {url}")
    print(f"Params: {test_params}")
    print("-" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=test_params)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nParsed Response:")
                print(f"  Status: {data.get('status')}")
                print(f"  URL: {data.get('url', 'N/A')[:100]}")
                print(f"  Message: {data.get('message', 'N/A')}")
                
                return True
            else:
                print(f"\nERROR: Non-200 status code")
                return False
                
    except Exception as e:
        print(f"\nEXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_stream_endpoint())
    sys.exit(0 if result else 1)
