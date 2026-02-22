import sys
import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import CORS_ORIGINS, BACKEND_PORT
from database import init_db
from api import scans, reports, fix_loop

# Force UTF-8 encoding on Windows to prevent charmap codec errors
if sys.platform == 'win32':
    # Set UTF-8 mode for all file operations
    os.environ.setdefault('PYTHONUTF8', '1')
    # Reconfigure stdout/stderr to use UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    # Set Windows event loop policy - Selector required for Playwright subprocess support
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="GoNoGo API",
    description="AI-powered QA and design evaluation agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
app.include_router(reports.router, prefix="/api/scans", tags=["reports"])
app.include_router(fix_loop.router, prefix="/api/scans", tags=["fix-loop"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "gonogo", "version": "2026.2.22a"}


if __name__ == "__main__":
    import uvicorn
    # Run without reload on Windows to ensure event loop policy persists
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=False)
