import sys
import enum

# Polyfill StrEnum for Python < 3.11 (since throttlebuster requires it)
if not hasattr(enum, 'StrEnum'):
    class StrEnum(str, enum.Enum):
        def __str__(self):
            return str(self.value)
    enum.StrEnum = StrEnum

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router as api_router

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="MovieBox Web App", description="API for MovieBox Web App")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile app access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
@app.head("/")
async def root():
    return {"message": "Welcome to MovieBox API"}

@app.get("/api/health")
@app.head("/api/health")
async def health_check():
    return {"status": "ok"}

