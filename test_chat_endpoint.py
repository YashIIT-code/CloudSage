from fastapi.testclient import TestClient
from main import app
import os

print("Loaded API Key Length:", len(os.environ.get("GEMINI_API_KEY", "")))

client = TestClient(app)

print("\n--- Testing Single Turn ---")
response1 = client.post("/api/chat", json={
    "message": "Hi ARIA, I have 5 idle VMs.",
    "context": "Fleet test data",
    "history": []
})
reply1 = response1.json().get("reply", "")
print("User: Hi ARIA, I have 5 idle VMs.")
print("ARIA:", reply1)

print("\n--- Testing Multi-Turn (History) ---")
response2 = client.post("/api/chat", json={
    "message": "What should I do with them? Give me exactly one sentence.",
    "context": "Fleet test data",
    "history": [
        {"role": "user", "text": "Hi ARIA, I have 5 idle VMs."},
        {"role": "ai", "text": reply1}
    ]
})
reply2 = response2.json().get("reply", "")
print("User: What should I do with them? Give me exactly one sentence.")
print("ARIA:", reply2)
