"""
CloudSage – /api/analyze router.
Runs pricing, inefficiency detection, and Gemini AI analysis.
"""

from fastapi import APIRouter

from backend.models.schemas import AnalysisResponse, AnalyzeRequest, Recommendation
from backend.services.inefficiency import calculate_efficiency_score, detect_inefficiencies
from backend.services.pricing import calculate_resource_cost, get_optimized_cost
from backend.services.gemini_service import get_analysis

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest):
    """Full analysis pipeline: pricing → inefficiency → Gemini AI."""

    all_inefficiencies = []
    current_monthly_cost = 0.0
    optimized_monthly_cost = 0.0

    # 1. Pricing & inefficiency for each resource
    resource_summaries = []
    for res in request.resources:
        cost = calculate_resource_cost(res)
        optimized = get_optimized_cost(res)
        saving = cost - optimized
        
        current_monthly_cost += cost
        optimized_monthly_cost += optimized
        
        # DEBUG print for verification
        print(f"DEBUG: Resource {res.resource_id} (Provider: {res.provider.value}, Type: {res.resource_type.value}, Size: {res.instance_type}, Hours: {res.hours_per_day}) -> Cost: {cost}")

        issues = detect_inefficiencies(res)
        all_inefficiencies.extend(issues)

        resource_summaries.append({
            "resource_id": res.resource_id,
            "provider": res.provider.value,
            "type": res.resource_type.value,
            "region": res.region,
            "instance_type": res.instance_type,
            "environment": res.environment.value,
            "cpu": res.cpu_utilization,
            "memory": res.memory_utilization,
            "storage_gb": res.storage_gb,
            "monthly_cost": cost,
            "optimized_cost": optimized,
            "saving": saving,
        })

    # Calculate overall savings
    total_savings = current_monthly_cost - optimized_monthly_cost
    if current_monthly_cost > 0:
        savings_percentage = (total_savings / current_monthly_cost) * 100
    else:
        savings_percentage = 0.0

    # 2. Efficiency score
    score = calculate_efficiency_score(all_inefficiencies)

    # 3. Gemini AI analysis
    ai_data = {
        "resources": resource_summaries,
        "total_monthly_cost": round(current_monthly_cost, 2),
        "total_potential_savings": round(total_savings, 2),
        "efficiency_score": score,
        "inefficiency_count": len(all_inefficiencies),
    }
    ai_result = await get_analysis(ai_data)

    # 4. Build recommendations from AI response
    recommendations = []
    for rec in ai_result.get("recommendations", []):
        recommendations.append(Recommendation(
            title=rec.get("title", "Optimisation Recommendation"),
            description=rec.get("description", ""),
            estimated_saving=rec.get("estimated_saving", 0),
            effort=rec.get("effort", "medium"),
            priority=rec.get("priority", 3),
            cli_command=rec.get("cli_command", ""),
            terraform_snippet=rec.get("terraform_snippet", ""),
        ))

    return AnalysisResponse(
        resources=request.resources,
        inefficiencies=all_inefficiencies,
        recommendations=recommendations,
        efficiency_score=score,
        current_monthly_cost=round(current_monthly_cost, 2),
        optimized_monthly_cost=round(optimized_monthly_cost, 2),
        total_savings=round(total_savings, 2),
        savings_percentage=round(savings_percentage, 2),
        executive_summary=ai_result.get("executive_summary", ""),
    )
