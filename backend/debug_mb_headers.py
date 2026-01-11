from moviebox import Session

s = Session()
print("Session headers:", getattr(s, '_headers', 'Not Found'))
if hasattr(s, '_client'):
    print("Client headers:", getattr(s._client, 'headers', 'Not Found'))
