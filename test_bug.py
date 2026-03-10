import os

# clear environment variable first
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]

from routers import analyze
import asyncio

# NOW load dotenv, mimicking main.py
from dotenv import load_dotenv
load_dotenv()

async def test():
    req = analyze.ChatRequest(message="Hello", context="Test")
    res = await analyze.chat_with_aria(req)
    print("Response:", res)

if __name__ == "__main__":
    asyncio.run(test())
