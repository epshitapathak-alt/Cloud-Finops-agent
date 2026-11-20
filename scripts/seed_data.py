import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.session import SessionLocal, init_db
from backend.app.services.dataset_loader import load_synthetic_dataset

def main():
    init_db()
    db = SessionLocal()
    try:
        count = load_synthetic_dataset(db, force_reload=True)
        print(f"Successfully loaded {count} synthetic cloud resources into database.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
