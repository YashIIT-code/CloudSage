"""
CloudSage – /api/chat router.
Interactive ARIA chat with history and analysis context.
"""

import re
from fastapi import APIRouter

from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.gemini_service import chat_with_aria

router = APIRouter()


def _strip_html(text: str) -> str:
    """Remove HTML tags from user input."""
    return re.sub(r"<[^>]+>", "", text)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to ARIA and receive a reply."""

    message = _strip_html(request.message)
    context = _strip_html(request.context)

    reply = await chat_with_aria(
        message=message,
        context=context,
        history=request.history if request.history else None,
    )

    return ChatResponse(reply=reply)
