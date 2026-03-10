"""
CloudSage Analysis Router
==========================
POST /analyze — full calculation pipeline (pure Python math)
POST /chat    — ARIA AI advisor (Gemini, new SDK)
"""
from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel

from models import (
    AnalyzeRequest, AnalysisResponse, ResourceCost,
    Inefficiency, Recommendation,
)
from pricing import calculate_resource_cost, get_optimized_cost
from inefficiency import detect_inefficiencies, calculate_efficiency_score
from services.gemini_service import generate_ai_analysis

router = APIRouter()


# ──────────────────────────────────────────────
#  POST /api/analyze  —  the main analysis brain
# ──────────────────────────────────────────────
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest):
    resources = request.resources

    # Step 1: Calculate all costs using pricing tables
    costs = []
    optimized_costs = []
    opt_reasons = []
    for resource in resources:
        cost = calculate_resource_cost(resource)
        opt, why = get_optimized_cost(resource, cost)
        costs.append(cost)
        optimized_costs.append(opt)
        opt_reasons.append(why)
        print(f"[ANALYZE] {resource.resource_name}: ${cost:.2f} -> ${opt:.2f} ({why})")

    # Step 2: Detect inefficiencies + calculate efficiency score
    ineff_dicts = detect_inefficiencies(resources, costs)
    inefficiencies = [Inefficiency(**item) for item in ineff_dicts]
    efficiency_score = calculate_efficiency_score(ineff_dicts)

    # Step 3: Totals
    current_total   = round(sum(costs), 2)
    optimized_total = round(sum(optimized_costs), 2)
    total_savings   = round(current_total - optimized_total, 2)
    savings_pct     = round((total_savings / current_total * 100) if current_total > 0 else 0, 1)

    # Step 4: Per-resource breakdown
    breakdown = [
        ResourceCost(
            resource_name  = r.resource_name,
            type           = str(r.type).replace("ResourceType.", ""),
            provider       = str(r.provider).replace("Provider.", ""),
            monthly_cost   = costs[i],
            optimized_cost = optimized_costs[i],
            saving         = round(costs[i] - optimized_costs[i], 2),
        )
        for i, r in enumerate(resources)
    ]

    # Step 5: Gemini for text-only analysis
    try:
        gemini_result = await generate_ai_analysis(
            resources, efficiency_score, total_savings
        )
        analysis_text = gemini_result.get("executive_summary", "Analysis complete.")
        raw_recs = gemini_result.get("recommendations", [])
        recommendations = []
        for idx, rec in enumerate(raw_recs):
            recommendations.append(Recommendation(
                title=rec.get("title", f"Recommendation {idx + 1}"),
                description=rec.get("description", ""),
                estimated_saving=round(total_savings / max(len(raw_recs), 1), 2),
                effort="medium",
                priority=idx + 1,
                cli_command=rec.get("cli_command"),
                terraform_snippet=rec.get("terraform_snippet"),
            ))
    except Exception as e:
        print(f"[GEMINI] Error: {e}")
        analysis_text = (
            f"Your infrastructure costs ${current_total:.2f}/month. "
            f"We identified ${total_savings:.2f} in potential savings ({savings_pct}% reduction). "
            f"Efficiency score: {efficiency_score}/100."
        )
        recommendations = []

    return AnalysisResponse(
        current_monthly_cost=current_total,
        optimized_monthly_cost=optimized_total,
        total_savings=total_savings,
        savings_percentage=savings_pct,
        efficiency_score=efficiency_score,
        breakdown=breakdown,
        inefficiencies=inefficiencies,
        analysis=analysis_text,
        recommendations=recommendations,
    )


# ──────────────────────────────────────────────
#  POST /api/chat  —  ARIA AI advisor (NEW SDK)
# ──────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    context: str
    history: Optional[list[ChatMessage]] = []

class ChatResponse(BaseModel):
    reply: str
    error: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_aria(req: ChatRequest):
    import os
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ChatResponse(
            reply="I am ARIA. Please set the GEMINI_API_KEY environment variable to interact with me!"
        )

    system_instruction = f"""You are ARIA, an Expert Cloud Advisor.
The user is asking a question about their cloud infrastructure.
Here is the context about their fleet:
{req.context}

Please provide a concise, technical, and helpful answer. Use markdown text format.
"""

    # Build conversation history
    contents = []
    if req.history:
        for msg in req.history:
            role = "model" if msg.role == "ai" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg.text}]
            })

    # Add current user message
    contents.append({
        "role": "user",
        "parts": [{"text": req.message}]
    })

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=contents,
            config={
                "system_instruction": system_instruction
            }
        )
        return ChatResponse(reply=response.text.strip())
    except Exception as e:
        return ChatResponse(reply=f"Error analyzing chat context: {str(e)}")