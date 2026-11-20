import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from backend.app.core.config import settings

def main():
    print("==================================================")
    print("  Autonomous Cloud FinOps Agent — Backend Server  ")
    print(f"  Live Dashboard: http://localhost:{settings.PORT}")
    print(f"  Swagger API:    http://localhost:{settings.PORT}/docs")
    print("==================================================")
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

if __name__ == "__main__":
    main()
