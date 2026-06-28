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

import os

@app.middleware("http")
async def override_cors_headers(request: Request, call_next):
    is_render = os.environ.get("RENDER") == "true" or "onrender.com" in str(request.url.netloc)

    if request.method == "OPTIONS":
        if is_render:
            return Response(status_code=204)
        origin = request.headers.get("Origin", "*")
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS, POST, PUT, DELETE",
                "Cross-Origin-Resource-Policy": "cross-origin",
            }
        )

    response = await call_next(request)
    
    if not is_render:
        origin = request.headers.get("Origin", "*")
        cors_keys = [
            "access-control-allow-origin",
            "access-control-allow-credentials",
            "access-control-allow-headers",
            "access-control-allow-methods",
            "access-control-expose-headers"
        ]
        for key in list(response.headers.keys()):
            if key.lower() in cors_keys:
                del response.headers[key]
                
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS, POST, PUT, DELETE"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    
    return response

app.include_router(api_router, prefix="/api")

@app.get("/")
@app.head("/")
async def root():
    return {"message": "Welcome to MovieBox API"}

@app.get("/api/health")
@app.head("/api/health")
async def health_check():
    return {"status": "ok"}

