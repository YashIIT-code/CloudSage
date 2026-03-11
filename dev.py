import uvicorn
import os
import sys

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting CloudSage Backend on http://localhost:8000")
    print("👉 Ensure npm run dev is also running on http://localhost:5173")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
