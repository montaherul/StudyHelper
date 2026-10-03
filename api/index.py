"""
LocalStudy FastAPI Serverless Entry Point for Vercel.
Includes universal path normalization to handle all Vercel serverless rewrite prefixes.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from api.web_ui import get_web_ui_html

app = FastAPI(
    title="LocalStudy API",
    version="1.0.0",
    description="Offline-first lecture processing toolkit and media downloader API.",
    docs_url="/docs",
    redoc_url="/redoc"
)


class VercelPathNormalizerMiddleware(BaseHTTPMiddleware):
    """
    Normalizes Vercel's internal serverless rewrite paths.
    Vercel often invokes serverless functions with prefixes like
    '/api/index.py', '/api/index', or '/api' when rewrites are used.
    This middleware ensures routes match cleanly regardless of proxy prefix.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        for prefix in ("/api/index.py", "/api/index", "/api"):
            if path == prefix:
                request.scope["path"] = "/"
                break
            elif path.startswith(prefix + "/"):
                request.scope["path"] = path[len(prefix):]
                break
        return await call_next(request)


# Enable Vercel path normalizer and CORS
app.add_middleware(VercelPathNormalizerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/app")
async def root(request: Request):
    """
    Serves the LocalStudy Web Studio UI for web browsers,
    or JSON status for programmatic API clients.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept or "application/xhtml+xml" in accept or "*/*" in accept or not accept:
        return HTMLResponse(content=get_web_ui_html())

    return {
        "application": "LocalStudy",
        "version": "1.0.0",
        "status": "online",
        "message": "LocalStudy Web Studio & API is running successfully on Vercel.",
        "endpoints": {
            "web_studio": "/",
            "health": "/health",
            "info": "/api/info",
            "docs": "/docs"
        }
    }


@app.get("/api/status")
@app.get("/status")
async def api_status():
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
@app.get("/info")
async def api_info():
    return {
        "name": "LocalStudy API",
        "version": "1.0.0",
        "description": "Offline-first lecture processing and universal media toolkit",
        "status": "online",
        "endpoints": [
            {"path": "/", "method": "GET", "desc": "Service status"},
            {"path": "/health", "method": "GET", "desc": "Health check"},
            {"path": "/docs", "method": "GET", "desc": "Interactive Swagger UI documentation"},
            {"path": "/api/info", "method": "GET", "desc": "API endpoint discovery"}
        ]
    }


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "application": "LocalStudy",
            "status": "online",
            "error": "Not Found",
            "requested_path": request.url.path,
            "available_endpoints": [
                {"path": "/", "desc": "API Home"},
                {"path": "/health", "desc": "Health Check"},
                {"path": "/docs", "desc": "API Documentation"},
                {"path": "/api/info", "desc": "Service Info"}
            ]
        }
    )
