"""
CloudSage – FastAPI application entry point.
"""

import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env before anything else
load_dotenv()

import sys
# Ensure the current directory is in the path for Railway imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from routers import analyze, parse_file, chat, optimize # noqa: E402

# ─── Logging ─────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger("cloudsage")

# ─── App ─────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CloudSage API",
    description="AI-powered cloud cost optimisation backend",
    version="2.1.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────────

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://cloud-sage-nine.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────────

app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(parse_file.router, prefix="/api", tags=["File Parsing"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(optimize.router, prefix="/api", tags=["Optimisation"])

# ─── Health check ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CloudSage API", "version": "2.1.0"}

# ─── Global exception handler ───────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"},
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True if os.environ.get("ENV") == "dev" else False)
