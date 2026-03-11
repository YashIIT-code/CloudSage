import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
from routers import analyze

async def test():
    print("Loaded API Key Length:", len(os.environ.get("GEMINI_API_KEY", "")))

    print("\n--- Testing Single Turn ---")
    req1 = analyze.ChatRequest(message="Hi ARIA, I have 5 idle VMs.", context="Fleet test data", history=[])
    res1 = await analyze.chat_with_aria(req1)
    reply1 = res1.reply
    print("User: Hi ARIA, I have 5 idle VMs.")
    print("ARIA:", reply1)

    print("\n--- Testing Multi-Turn (History) ---")
    req2 = analyze.ChatRequest(
        message="What should I do with them? Give me exactly one sentence.",
        context="Fleet test data",
        history=[
            analyze.ChatMessage(role="user", text="Hi ARIA, I have 5 idle VMs."),
            analyze.ChatMessage(role="ai", text=reply1)
        ]
    )
    res2 = await analyze.chat_with_aria(req2)
    reply2 = res2.reply
    print("User: What should I do with them? Give me exactly one sentence.")
    print("ARIA:", reply2)

if __name__ == "__main__":
    asyncio.run(test())
