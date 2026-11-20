import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.app.core.config import settings
from backend.app.database.session import init_db, SessionLocal
from backend.app.services.dataset_loader import load_synthetic_dataset
from backend.app.api.routes import router as api_router

# Initialize database schema
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous Cloud Cost Optimization & Infrastructure Remediation Agent API",
    version="1.0.0"
)

# Enable CORS for local development and browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    if INDEX_HTML.exists():
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Autonomous Cloud FinOps Agent API</h1><p>Visit <a href='/docs'>/docs</a> for API specifications.</p>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
