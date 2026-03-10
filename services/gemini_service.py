"""
CloudSage Gemini Service
========================
Uses the NEW google.genai SDK (replaces deprecated google.generativeai).
"""
import os
from google import genai
import json


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables")
    return genai.Client(api_key=api_key)


async def generate_ai_analysis(resources, efficiency_score: int, total_savings: float) -> dict:
    """
    Generate executive summary + recommendations using Gemini.
    Returns a dict with 'executive_summary' and 'recommendations'.
    """
    client = get_client()

    resource_summary = "\n".join([
        f"- {r.resource_name} ({str(r.type)} on {str(r.provider)}, region: {r.region})"
        for r in resources
    ])

    prompt = f"""You are ARIA, an expert Cloud Cost Optimization Advisor.

Analyze the following cloud resources and provide optimization recommendations.

RESOURCES:
{resource_summary}

CALCULATED METRICS:
- Efficiency Score: {efficiency_score}/100
- Total Potential Savings: ${total_savings:.2f}/month

Respond ONLY with a valid JSON object in this exact format (no markdown, no backticks):
{{
  "executive_summary": "2-3 sentence summary of the cloud infrastructure state and key findings",
  "recommendations": [
    {{
      "title": "Short title",
      "description": "Detailed explanation of the recommendation",
      "cli_command": "aws/gcloud/az CLI command if applicable, else null",
      "terraform_snippet": "Terraform HCL snippet if applicable, else null"
    }}
  ]
}}

Provide 3-5 recommendations. Be specific with CLI commands and Terraform snippets where possible.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt
    )

    raw = response.text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "executive_summary": raw[:500] if raw else "Analysis complete.",
            "recommendations": []
        }
