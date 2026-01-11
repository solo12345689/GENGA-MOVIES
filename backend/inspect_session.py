
try:
    from moviebox_api import Session
    import httpx
    
    s = Session()
    with open("session_inspection.txt", "w") as f:
        f.write(f"Session: {s}\n")
        f.write(f"Has _headers: {hasattr(s, '_headers')}\n")
        if hasattr(s, '_headers'):
            f.write(f"Headers: {s._headers}\n")
        
        # Look for httpx client
        for attr in dir(s):
            val = getattr(s, attr, None)
            if isinstance(val, (httpx.Client, httpx.AsyncClient)):
                f.write(f"Found client in {attr}\n")
                f.write(f"Client headers: {val.headers}\n")
                f.write(f"Client cookies: {dict(val.cookies)}\n")
except Exception as e:
    with open("session_inspection.txt", "w") as f:
        f.write(f"Error: {e}\n")
