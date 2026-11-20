import json
import os
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.database.models import ResourceModel

DATA_FILE_PATH = Path(__file__).resolve().parents[3] / "data" / "synthetic_cloud_data.json"

def load_synthetic_dataset(db: Session, force_reload: bool = False) -> int:
    """Load synthetic cloud resources into the database."""
    existing_count = db.query(ResourceModel).count()
    if existing_count > 0 and not force_reload:
        return existing_count

    if not DATA_FILE_PATH.exists():
        raise FileNotFoundError(f"Synthetic dataset not found at {DATA_FILE_PATH}")

    with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    inserted = 0
    for item in records:
        resource = db.query(ResourceModel).filter_by(resource_id=item["resource_id"]).first()
        if not resource:
            resource = ResourceModel(
                resource_id=item["resource_id"],
                resource_name=item["resource_name"],
                resource_type=item["resource_type"],
                instance_type=item.get("instance_type"),
                cpu_utilization=item.get("cpu_utilization", 0.0),
                memory_utilization=item.get("memory_utilization", 0.0),
                monthly_cost=item["monthly_cost"],
                region=item["region"],
                environment=item["environment"],
                resource_status=item.get("resource_status", "running"),
                criticality=item.get("criticality", "low"),
                last_activity=item.get("last_activity"),
                tags=item.get("tags", {})
            )
            db.add(resource)
            inserted += 1
        elif force_reload:
            resource.resource_name = item["resource_name"]
            resource.resource_type = item["resource_type"]
            resource.instance_type = item.get("instance_type")
            resource.cpu_utilization = item.get("cpu_utilization", 0.0)
            resource.memory_utilization = item.get("memory_utilization", 0.0)
            resource.monthly_cost = item["monthly_cost"]
            resource.region = item["region"]
            resource.environment = item["environment"]
            resource.resource_status = item.get("resource_status", "running")
            resource.criticality = item.get("criticality", "low")
            resource.last_activity = item.get("last_activity")
            resource.tags = item.get("tags", {})

    db.commit()
    return db.query(ResourceModel).count()
