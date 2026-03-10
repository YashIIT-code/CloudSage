"""
CloudSage – Google Gemini integration service.
Provides ARIA (AI Resource Intelligence Advisor) persona for cloud analysis and chat.
"""

import json
import os
import re

import google.generativeai as genai

# ─── Configuration ───────────────────────────────────────────────────────────────

_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if _API_KEY:
    genai.configure(api_key=_API_KEY)

_MODEL_NAME = "gemini-2.5-flash"

ARIA_SYSTEM_PROMPT = (
    "You are ARIA — AI Resource Intelligence Advisor. "
    "You are an expert Cloud Cost Optimization Advisor with deep knowledge of AWS, Azure, and GCP. "
    "You provide technical, concise, and actionable advice. "
    "Always be helpful and professional. "
    "When asked for analysis, return ONLY valid JSON (no markdown fences, no extra text)."
)


def _strip_html(text: str) -> str:
    """Remove HTML tags from user-supplied strings."""
    return re.sub(r"<[^>]+>", "", text)


def _is_configured() -> bool:
    """Return True when a real API key is available."""
    return bool(_API_KEY) and _API_KEY != "your_gemini_api_key_here"


# ─── Analysis ────────────────────────────────────────────────────────────────────

async def get_analysis(data: dict) -> dict:
    """
    Send fleet data to Gemini and request a structured analysis.
    Returns a dict with ``executive_summary`` and ``recommendations``.
    """
    if not _is_configured():
        return _mock_analysis(data)

    prompt = (
        f"{ARIA_SYSTEM_PROMPT}\n\n"
        "Analyse the following cloud resource data and return ONLY valid JSON with these keys:\n"
        '  "executive_summary": "<string>",\n'
        '  "recommendations": [\n'
        '    {\n'
        '      "title": "<string>",\n'
        '      "description": "<string>",\n'
        '      "estimated_saving": <number>,\n'
        '      "effort": "low|medium|high",\n'
        '      "priority": <1-5>,\n'
        '      "cli_command": "<AWS/Azure/GCP CLI command>",\n'
        '      "terraform_snippet": "<Terraform HCL>"\n'
        '    }\n'
        "  ]\n"
        "Provide exactly 3 specific, actionable recommendations.\n\n"
        f"Cloud Fleet Data:\n{json.dumps(data, indent=2)}"
    )

    try:
        model = genai.GenerativeModel(_MODEL_NAME)
        response = await model.generate_content_async(prompt)
        text = response.text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return _mock_analysis(data)


# ─── Chat ────────────────────────────────────────────────────────────────────────

async def chat_with_aria(message: str, context: str = "", history: list[dict] | None = None) -> str:
    """
    Interactive chat with the ARIA persona.
    ``history`` is a list of dicts with ``role`` ("user"/"model") and ``parts`` keys.
    """
    message = _strip_html(message)
    context = _strip_html(context)

    if not _is_configured():
        return (
            f"(Mock mode) I am ARIA. I received your message: \"{message}\". "
            "Please set a valid GEMINI_API_KEY in your .env for real AI responses."
        )

    full_prompt = (
        f"{ARIA_SYSTEM_PROMPT}\n\n"
        f"Current Cloud Fleet Context:\n{context}\n\n"
        f"User Question: {message}"
    )

    try:
        model = genai.GenerativeModel(_MODEL_NAME)

        # Build chat history if provided
        if history:
            if history and history[0].get("role") == "model":
                history = history[1:]
            chat = model.start_chat(history=history)
            response = await chat.send_message_async(full_prompt)
        else:
            response = await model.generate_content_async(full_prompt)

        return response.text
    except Exception as exc:
        return f"ARIA encountered an error: {exc}"


# ─── Fallback mock ──────────────────────────────────────────────────────────────

def _mock_analysis(data: dict) -> dict:
    """Return a realistic mock analysis when Gemini is unavailable."""
    resource_count = len(data.get("resources", []))
    return {
        "executive_summary": (
            f"Analysis of {resource_count} cloud resources reveals significant optimisation opportunities. "
            "Several dev/staging workloads are running 24/7, and multiple VMs show CPU utilisation below 20%. "
            "Implementing the recommendations below could reduce monthly spend by 30–45%."
        ),
        "recommendations": [
            {
                "title": "Implement Auto-Shutdown for Dev/Staging Environments",
                "description": "Schedule non-production workloads to shut down outside business hours (evenings & weekends).",
                "estimated_saving": 850.0,
                "effort": "low",
                "priority": 1,
                "cli_command": "aws ec2 create-tags --resources i-xxx --tags Key=AutoStop,Value=true && aws scheduler create-schedule --name dev-shutdown --schedule-expression 'cron(0 19 ? * MON-FRI *)'",
                "terraform_snippet": 'resource "aws_instance" "dev" {\n  instance_type = "t3.medium"\n  tags = {\n    AutoStop = "true"\n    Schedule = "business-hours-only"\n  }\n}',
            },
            {
                "title": "Right-Size Over-Provisioned VMs",
                "description": "Downsize instances with <20% CPU to the next smaller tier to match actual workload demands.",
                "estimated_saving": 620.0,
                "effort": "medium",
                "priority": 2,
                "cli_command": "aws ec2 modify-instance-attribute --instance-id i-xxx --instance-type '{\"Value\": \"t3.small\"}'",
                "terraform_snippet": 'resource "aws_instance" "web" {\n  instance_type = "t3.small"  # downsized from t3.xlarge\n}',
            },
            {
                "title": "Migrate Cold Storage to Archive Tier",
                "description": "Move infrequently accessed data (>100 GB hot storage) to Glacier/Coldline to cut storage costs by 44%.",
                "estimated_saving": 340.0,
                "effort": "low",
                "priority": 3,
                "cli_command": "aws s3api put-bucket-lifecycle-configuration --bucket my-bucket --lifecycle-configuration file://lifecycle.json",
                "terraform_snippet": 'resource "aws_s3_bucket_lifecycle_configuration" "archive" {\n  bucket = aws_s3_bucket.data.id\n  rule {\n    id     = "archive-old"\n    status = "Enabled"\n    transition {\n      days          = 30\n      storage_class = "GLACIER"\n    }\n  }\n}',
            },
        ],
    }
