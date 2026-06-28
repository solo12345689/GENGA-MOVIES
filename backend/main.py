import sys
import enum

# Polyfill StrEnum for Python < 3.11 (since throttlebuster requires it)
if not hasattr(enum, 'StrEnum'):
    class StrEnum(str, enum.Enum):
        def __str__(self):
            return str(self.value)
    enum.StrEnum = StrEnum

import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from api import router as api_router

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="MovieBox Web App", description="API for MovieBox Web App")

class ASGICORSMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Handle OPTIONS preflight requests directly at ASGI layer
        if scope.get("method") == "OPTIONS":
            origin = "*"
            for key, val in scope.get("headers", []):
                if key.lower() == b"origin":
                    origin = val.decode("utf-8")
                    break
            
            headers = [
                (b"content-length", b"0"),
                (b"access-control-allow-origin", origin.encode("utf-8")),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-allow-methods", b"GET, OPTIONS, POST, PUT, DELETE"),
                (b"access-control-allow-headers", b"*"),
                (b"cross-origin-resource-policy", b"cross-origin")
            ]
            
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": headers
            })
            await send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False
            })
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                origin = "*"
                for key, val in scope.get("headers", []):
                    if key.lower() == b"origin":
                        origin = val.decode("utf-8")
                        break

                headers = []
                cors_keys = [
                    b"access-control-allow-origin",
                    b"access-control-allow-credentials",
                    b"access-control-allow-headers",
                    b"access-control-allow-methods",
                    b"access-control-expose-headers"
                ]
                
                # Strip duplicate/pre-existing CORS headers
                for key, val in message.get("headers", []):
                    if key.lower() in cors_keys:
                        continue
                    headers.append((key, val))

                # Inject singular CORS headers
                headers.append((b"access-control-allow-origin", origin.encode("utf-8")))
                headers.append((b"access-control-allow-credentials", b"true"))
                headers.append((b"access-control-allow-methods", b"GET, OPTIONS, POST, PUT, DELETE"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"cross-origin-resource-policy", b"cross-origin"))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(ASGICORSMiddleware)

app.include_router(api_router, prefix="/api")

@app.get("/")
@app.head("/")
async def root():
    return {"message": "Welcome to MovieBox API"}

@app.get("/api/health")
@app.head("/api/health")
async def health_check():
    return {"status": "ok"}

