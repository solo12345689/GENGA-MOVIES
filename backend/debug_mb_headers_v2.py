from moviebox_api import Session
import httpx

s = Session()
print("Session obj:", s)
# Try to find headers
if hasattr(s, '_headers'):
    print("Session._headers:", s._headers)
# Try to find client
for attr in dir(s):
    val = getattr(s, attr)
    if isinstance(val, httpx.Client) or isinstance(val, httpx.AsyncClient):
        print(f"Found client in {attr}")
        print("  Headers:", val.headers)
