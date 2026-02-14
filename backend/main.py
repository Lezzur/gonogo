import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import CORS_ORIGINS, BACKEND_PORT
from database import init_db
from api import scans, reports

# Set Windows event loop policy before anything else
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "gonogo"}


if __name__ == "__main__":
    import uvicorn
    # Run without reload on Windows to ensure event loop policy persists
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=False)
