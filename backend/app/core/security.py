import re
import shlex

# Safe alphanumeric pattern for AWS resource identifiers
RESOURCE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_.]+$")

# Allowlisted actions for Terraform generator
ALLOWED_ACTIONS = {
    "DOWNSIZE_INSTANCE",
    "DELETE_UNATTACHED_VOLUME",
    "DOWNSIZE_DATABASE",
    "APPLY_S3_LIFECYCLE_TIER",
    "NO_ACTION"
}

# Allowlisted Terraform resource types
ALLOWED_TERRAFORM_RESOURCES = {
    "aws_instance",
    "aws_ebs_volume",
    "aws_db_instance",
    "aws_s3_bucket_lifecycle_configuration"
}

def sanitize_string(value: str, max_length: int = 120) -> str:
    """Sanitize strings to prevent command and prompt injection."""
    if not value:
        return ""
    # Strip dangerous characters
    cleaned = re.sub(r"[^\w\s\-_.:/]", "", str(value))
    return cleaned.strip()[:max_length]

def validate_resource_id(resource_id: str) -> bool:
    """Ensure resource_id conforms strictly to safe cloud identifier rules."""
    if not resource_id or len(resource_id) > 64:
        return False
    return bool(RESOURCE_ID_PATTERN.match(resource_id))
