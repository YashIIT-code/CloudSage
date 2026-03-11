from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/ping")
async def ping():
    return {"status": "pong", "message": "Vercel API route is working"}
