import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import analyze

app = FastAPI(
    title="CloudSage Backend",
    description="Professional Python Backend for Cloud Architecture Analysis",
    version="1.0.0"
)

# Robust CORS Configuration: Allow Local Vite and Dynamically Assigned Vercel domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global API Exception Handler to enforce structured JSON boundaries
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )

# Include core analysis router
app.include_router(analyze.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "success", "message": "CloudSage API is alive and running."}

# Enable local testing and fast feedback loop (python -m backend.main)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
