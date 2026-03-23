"""
CloudSage ARIA Chatbot
======================
AI cost optimization advisor that uses OpenAI, Google Gemini, or a
rule-based fallback to answer user questions with context from the
uploaded cost data.
"""

import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ARIA system prompt
ARIA_SYSTEM_PROMPT = (
    "You are ARIA, an AI cloud cost optimization advisor built into CloudSage. "
    "Analyze the user's cloud cost data and provide clear, practical, and actionable "
    "insights. Be specific — reference actual services, dollar amounts, and percentages "
    "from the data. Use bullet points for recommendations. Keep responses concise but "
    "thorough. If you don't have enough data to answer, say so honestly. "
    "Always end your response with 3 short follow-up questions the user could ask, "
    "formatted exactly like this at the very end:\n"
    "SUGGESTIONS:\n- <question 1>\n- <question 2>\n- <question 3>"
)


async def chat_with_aria(
    user_message: str,
    context: dict[str, Any] | None = None,
) -> dict:
    """
    Process a user message and return ARIA's response.

    Tries providers in order: OpenAI → Gemini → rule-based fallback.

    Args:
        user_message: The user's question/query
        context: Optional dict with analysis/optimization context

    Returns:
        dict with response, provider, context_used, and suggestions list
    """
    context_text = _build_context_text(context) if context else ""

    # Try OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        result = await _call_openai(user_message, context_text, openai_key)
        if result:
            return result

    # Try Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        result = await _call_gemini(user_message, context_text, gemini_key)
        if result:
            return result

    # Fallback: rule-based response
    return _rule_based_response(user_message, context)


def _build_context_text(context: dict[str, Any]) -> str:
    """Build a concise text summary of the cost data for the LLM prompt."""
    parts = []

    # Analysis context
    analysis = context.get("analysis", {})
    if analysis:
        total = analysis.get("total_cost", 0)
        velocity = analysis.get("cost_velocity", "Unknown")
        parts.append(f"Total cloud spend: ${total:.2f}")
        if velocity != "Unknown":
            parts.append(f"Cost Velocity: {velocity}")

        top_services = analysis.get("top_services", [])
        if top_services:
            svc_lines = [
                f"  - {s['service']}: ${s['cost']:.2f} ({s['percentage']}%)"
                for s in top_services
            ]
            parts.append("Top services by cost:\n" + "\n".join(svc_lines))

        anomalies = analysis.get("anomalies", [])
        if anomalies:
            anom_lines = [f"  - [{a.get('severity', 'high').upper()}] {a['detail']}" for a in anomalies[:5]]
            parts.append("Detected anomalies:\n" + "\n".join(anom_lines))

    # Forecast context
    forecast = context.get("forecast", {})
    if forecast:
        trend = forecast.get('trend', 'unknown')
        method = forecast.get('method', 'unknown')
        parts.append(
            f"Forecast ({method}): Trending {trend}. "
            f"Predicted ${forecast.get('predicted_cost_next_7_days', 0):.2f} next 7 days, "
            f"${forecast.get('predicted_cost_next_30_days', 0):.2f} next 30 days."
        )

    # Optimisation context
    optimization = context.get("optimization", {})
    if optimization:
        recs = optimization.get("recommendations", [])
        savings_pct = optimization.get("total_potential_savings_pct", 0)
        savings_usd = optimization.get("total_potential_savings_usd", 0.0)
        if recs:
            rec_lines = [f"  - [Score: {r.get('priority_score', 0)}/10] {r['message']} (Saves ~${r.get('estimated_savings_usd', 0):.2f})" for r in recs[:5]]
            parts.append(
                f"Optimization (Potential Savings: ${savings_usd:.2f} / {savings_pct}%):\n"
                + "\n".join(rec_lines)
            )

    return "\n\n".join(parts) if parts else "No cost data has been uploaded yet."


def _parse_suggestions(reply_text: str) -> tuple[str, list[str]]:
    """Extract SUGGESTIONS: block from the LLM reply."""
    if "SUGGESTIONS:" not in reply_text:
        return reply_text, []
    
    parts = reply_text.split("SUGGESTIONS:")
    main_text = parts[0].strip()
    suggestions_text = parts[1].strip()
    
    suggestions = [
        line.lstrip("- ").strip() 
        for line in suggestions_text.split("\n") 
        if line.strip() and line.strip().startswith("-")
    ]
    return main_text, suggestions


async def _call_openai(
    user_message: str, context_text: str, api_key: str
) -> dict | None:
    """Call OpenAI's chat completion API."""
    try:
        import openai

        client = openai.AsyncOpenAI(api_key=api_key)

        messages = [
            {"role": "system", "content": ARIA_SYSTEM_PROMPT},
        ]
        if context_text:
            messages.append({
                "role": "system",
                "content": f"Here is the user's current cloud cost data:\n\n{context_text}",
            })
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=800,
            temperature=0.7,
        )

        reply = response.choices[0].message.content.strip()
        main_text, suggestions = _parse_suggestions(reply)
        
        logger.info("ARIA response generated via OpenAI")
        return {
            "response": main_text,
            "suggestions": suggestions,
            "provider": "openai",
            "context_used": bool(context_text),
        }
    except Exception as e:
        logger.warning(f"OpenAI call failed: {e}")
        return None


async def _call_gemini(
    user_message: str, context_text: str, api_key: str
) -> dict | None:
    """Call Google Gemini's generative AI API."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")

        prompt_parts = [ARIA_SYSTEM_PROMPT]
        if context_text:
            prompt_parts.append(
                f"Here is the user's current cloud cost data:\n\n{context_text}"
            )
        prompt_parts.append(f"User question: {user_message}")

        response = model.generate_content("\n\n".join(prompt_parts))
        reply = response.text.strip()
        main_text, suggestions = _parse_suggestions(reply)

        logger.info("ARIA response generated via Gemini")
        return {
            "response": main_text,
            "suggestions": suggestions,
            "provider": "gemini",
            "context_used": bool(context_text),
        }
    except Exception as e:
        logger.warning(f"Gemini call failed: {e}")
        return None


def _rule_based_response(
    user_message: str, context: dict[str, Any] | None
) -> dict:
    """
    Generate a helpful response without an LLM by using the analysis data
    directly. Covers common user queries.
    """
    msg_lower = user_message.lower()
    analysis = (context or {}).get("analysis", {})
    optimization = (context or {}).get("optimization", {})
    forecast = (context or {}).get("forecast", {})

    # No context available
    if not analysis and not optimization and not forecast:
        return {
            "response": (
                "👋 I'm ARIA, your cloud cost advisor! Please upload a CSV file "
                "first using the Dashboard, and I'll be able to analyze your costs "
                "and provide personalized recommendations.\n\n"
                "To enable AI-powered responses, set the `OPENAI_API_KEY` or "
                "`GEMINI_API_KEY` environment variable."
            ),
            "suggestions": ["What formats do you support?", "How does the optimizer work?"],
            "provider": "rule_based",
            "context_used": False,
        }

    total_cost = analysis.get("total_cost", 0)
    top_services = analysis.get("top_services", [])
    anomalies = analysis.get("anomalies", [])
    recs = optimization.get("recommendations", [])

    # --- Query: Why is cost high? ---
    if any(kw in msg_lower for kw in ["why", "high", "expensive", "much", "spike"]):
        lines = [f"📊 **Your total cloud spend is ${total_cost:.2f}.**\n"]
        if top_services:
            lines.append("**Top cost drivers:**")
            for s in top_services[:3]:
                lines.append(f"  • {s['service']}: ${s['cost']:.2f} ({s['percentage']}%)")
        if anomalies:
            lines.append("\n**⚠️ Anomalies detected:**")
            for a in anomalies[:3]:
                lines.append(f"  • [{a.get('severity', 'high').upper()}] {a['detail']}")
        lines.append(
            "\nTo reduce costs, check the optimization section."
        )
        return {
            "response": "\n".join(lines),
            "suggestions": ["How can I reduce my costs?", "What is the forecast for next month?"],
            "provider": "rule_based",
            "context_used": True,
        }

    # --- Query: How to reduce / save / optimize? ---
    if any(kw in msg_lower for kw in ["reduce", "save", "cut", "optimize", "lower", "decrease"]):
        lines = ["💡 **Here are your top optimization recommendations (sorted by priority):**\n"]
        if recs:
            for r in recs[:4]:
                lines.append(f"  • **{r['category'].replace('_', ' ').title()}**: {r['message']}")
        else:
            lines.append("  • No urgent recommendations — your infrastructure looks relatively efficient!")
        
        savings_usd = optimization.get("total_potential_savings_usd", 0.0)
        savings_pct = optimization.get("total_potential_savings_pct", 0)
        if savings_usd > 0:
            lines.append(f"\n**Estimated potential savings: ~${savings_usd:.2f}** ({savings_pct}% of total spend).")
        return {
            "response": "\n".join(lines),
            "suggestions": ["Are there any anomalies?", "Show me the top services."],
            "provider": "rule_based",
            "context_used": True,
        }

    # --- Query: Forecast / prediction ---
    if any(kw in msg_lower for kw in ["forecast", "predict", "future", "next", "trend"]):
        if forecast:
            trend = forecast.get("trend", "unknown")
            pred7 = forecast.get("predicted_cost_next_7_days", 0)
            pred30 = forecast.get("predicted_cost_next_30_days", 0)
            method = forecast.get("method", "unknown").replace("_", " ").title()
            
            lines = [
                f"📈 **Cost Forecast** (Method: {method})\n",
                f"  • **Trend:** {trend.title()}",
                f"  • **Next 7 days:** ${pred7:.2f}",
                f"  • **Next 30 days:** ${pred30:.2f}\n",
            ]
            
            if "confidence_interval_30d" in forecast:
                ci = forecast["confidence_interval_30d"]
                lines.append(f"  • *Estimated 30-day range: ${ci['lower']:.2f} to ${ci['upper']:.2f}*")
                
            lines.append(f"\n{'⚠️ Costs are trending upward — consider optimizing now.' if trend == 'increasing' else '✅ Costs appear stable or decreasing.'}")
            
            return {
                "response": "\n".join(lines),
                "suggestions": ["How can I reduce my costs?", "Why is my cost high?"],
                "provider": "rule_based",
                "context_used": True,
            }
        return {
            "response": "I don't have enough time-series data to generate a detailed forecast. Ensure your CSV has a Date column.",
            "suggestions": ["Show me the top services.", "How can I reduce my costs?"],
            "provider": "rule_based",
            "context_used": False,
        }

    # --- Default summary ---
    lines = [f"📊 **Cloud Cost Intelligence Summary:**\n"]
    lines.append(f"  • **Total Cost:** ${total_cost:.2f}")
    if top_services:
        lines.append(f"  • **Top Spender:** {top_services[0]['service']} (${top_services[0]['cost']:.2f})")
    if analysis.get('cost_velocity') and analysis['cost_velocity'] != "Unknown":
        lines.append(f"  • **Velocity:** {analysis['cost_velocity']}")
    
    if anomalies:
        lines.append(f"  • **🚨 Critical/High Anomalies:** {len([a for a in anomalies if a.get('severity') in ('critical', 'high')])}")
        
    savings_usd = optimization.get("total_potential_savings_usd", 0.0)
    if savings_usd > 0:
        lines.append(f"  • **💡 Potential Savings:** ~${savings_usd:.2f}")
        
    lines.append("\nAsk me about costs, forecasts, or how to optimise your cloud spend!")
    return {
        "response": "\n".join(lines),
        "suggestions": ["Why is my cost high?", "How can I reduce my costs?", "What is the forecast?"],
        "provider": "rule_based",
        "context_used": True,
    }
