"""
CloudSage — AI Cloud Cost Intelligence
=======================================
FastAPI application serving the cost calculation, analysis, forecasting,
optimization, and ARIA chatbot endpoints.
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.cost_service import process_csv_content
from services.analyzer import analyze_costs
from services.forecaster import forecast_costs
from services.optimizer import generate_optimizations
from services.chatbot import chat_with_aria

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CloudSage — AI Cloud Cost Intelligence",
    description=(
        "Production-grade cloud cost intelligence platform with analysis, "
        "forecasting, optimization, and AI advisor (ARIA)."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the frontend directory (sibling to backend)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ---------------------------------------------------------------------------
# In-memory session store for the last analysis context (used by /chat)
# In production this would be per-user/session; here we keep it simple.
# ---------------------------------------------------------------------------
_last_context: dict = {}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BreakdownItem(BaseModel):
    service: str
    usage: float
    unit_cost: float
    cost: float

class CostResponse(BaseModel):
    detected_columns: dict
    total_cost: float
    breakdown: List[BreakdownItem]

class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    provider: str
    context_used: bool

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/calculate-cost", response_model=CostResponse)
@app.post("/calculate-cost", response_model=CostResponse, include_in_schema=False)
async def calculate_cost(file: UploadFile = File(...)):
    """
    Legacy endpoint — accepts a CSV upload and returns cost calculation only.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV (.csv)")

    try:
        content = await file.read()
        result = process_csv_content(content)
        # Strip internal keys before returning
        return {
            "detected_columns": result["detected_columns"],
            "total_cost": result["total_cost"],
            "breakdown": result["breakdown"],
        }
    except ValueError as ve:
        logger.warning(f"Validation error during CSV processing: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while processing the CSV file")


@app.post("/api/v1/analyze")
@app.post("/analyze", include_in_schema=False)
async def full_analysis(file: UploadFile = File(...)):
    """
    Full intelligence pipeline — processes a CSV and returns combined
    calculation, analysis, forecast, and optimisation results.
    """
    global _last_context

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Uploaded file must be a CSV (.csv)")

    try:
        content = await file.read()

        # 1. Cost calculation
        calc_result = process_csv_content(content)

        # 2. Analysis
        analysis = analyze_costs(calc_result)

        # 3. Forecasting
        forecast = forecast_costs(calc_result)

        # 4. Optimisation
        optimization = generate_optimizations(calc_result, analysis)

        # Store context for ARIA chatbot
        _last_context = {
            "analysis": analysis,
            "forecast": forecast,
            "optimization": optimization,
        }

        # Build public response (strip private keys from calculation)
        response = {
            "calculation": {
                "detected_columns": calc_result["detected_columns"],
                "total_cost": calc_result["total_cost"],
                "breakdown": calc_result["breakdown"],
            },
            "analysis": analysis,
            "forecast": forecast,
            "optimization": optimization,
        }

        logger.info("Full analysis pipeline completed successfully")
        return JSONResponse(content=response)

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during analysis pipeline")


@app.post("/api/v1/chat", response_model=ChatResponse)
@app.post("/chat", response_model=ChatResponse, include_in_schema=False)
async def chat_endpoint(request: ChatRequest):
    """
    ARIA AI advisor chatbot — processes user questions with cost data context.
    """
    try:
        # Use provided context or fall back to stored context
        context = request.context or _last_context or None
        result = await chat_with_aria(request.message, context)
        return result
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing chat request")


@app.get("/api/v1/health", tags=["System"])
@app.get("/health", tags=["System"], include_in_schema=False)
def health_check():
    """Health status endpoint."""
    return {
        "status": "ok",
        "service": "cloudsage",
        "version": "2.0.0",
        "modules": ["calculator", "analyzer", "forecaster", "optimizer", "aria_chatbot"],
    }


# ---------------------------------------------------------------------------
# Frontend serving
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

# Mount frontend static files — MUST be last so it doesn't shadow API routes
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
