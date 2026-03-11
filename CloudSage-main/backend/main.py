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
