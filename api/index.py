"""
LocalStudy FastAPI Serverless Entry Point for Vercel.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="LocalStudy API",
    version="1.0.0",
    description="Offline-first lecture processing toolkit and media downloader API."
)

# Enable CORS for frontend and browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "application": "LocalStudy",
        "version": "1.0.0",
        "status": "online",
        "message": "LocalStudy API is running successfully on Vercel."
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/api/info")
async def api_info():
    return {
        "name": "LocalStudy API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "desc": "Service status"},
            {"path": "/health", "method": "GET", "desc": "Health check"},
            {"path": "/docs", "method": "GET", "desc": "Interactive Swagger API documentation"},
            {"path": "/api/info", "method": "GET", "desc": "API endpoint discovery"}
        ]
    }
