import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = "Autonomous Cloud FinOps Agent"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Database Configuration (SQLite default with PostgreSQL support)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finops_audit.db")
    
    # LLM Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Terraform CLI Integration
    TERRAFORM_BINARY_PATH: str = os.getenv("TERRAFORM_BINARY_PATH", "terraform")
    TERRAFORM_DIR: str = os.getenv("TERRAFORM_DIR", "./terraform")
    
    # Safety & Controls
    DRY_RUN_ONLY: bool = os.getenv("DRY_RUN_ONLY", "true").lower() == "true"
    REQUIRE_HUMAN_APPROVAL: bool = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() == "true"
    MAX_CORRECTION_RETRIES: int = int(os.getenv("MAX_CORRECTION_RETRIES", "3"))

settings = Settings()
