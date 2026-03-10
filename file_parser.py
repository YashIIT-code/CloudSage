"""
CloudSage File Parser
=====================
Parse CSV and JSON cloud resource data into validated dicts.
Handles BOM, whitespace, and validation.
"""
import csv
import json
import io
from typing import List

VALID_TYPES     = {"vm", "storage", "database", "container"}
VALID_PROVIDERS = {"azure", "aws", "gcp"}
VALID_ENVS      = {"production", "development", "staging"}


def clean(val) -> str:
    return str(val or "").strip().strip("\ufeff").lower()


def safe_float(val, default=None):
    try:
        v = float(str(val).strip())
        return v if v >= 0 else default
    except (ValueError, TypeError):
        return default


def parse_csv(file_content: bytes) -> List[dict]:
    """Parse CSV bytes into a list of resource dicts."""
    text   = file_content.decode("utf-8-sig").strip()
    reader = csv.DictReader(io.StringIO(text))
    resources = []
    for i, row in enumerate(reader):
        clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        rtype    = clean(clean_row.get("type", ""))
        provider = clean(clean_row.get("provider", ""))
        if rtype not in VALID_TYPES or provider not in VALID_PROVIDERS:
            continue
        env = clean(clean_row.get("environment", "production"))
        if env not in VALID_ENVS:
            env = "production"
        resources.append({
            "resource_name":      clean_row.get("resource_name", f"resource_{i+1}").strip(),
            "type":               rtype,
            "provider":           provider,
            "size":               clean_row.get("size", "").strip() or None,
            "storage_gb":         safe_float(clean_row.get("storage_gb"), 0.0),
            "region":             clean_row.get("region", "us-east-1").strip(),
            "hours_per_day":      safe_float(clean_row.get("hours_per_day"), 24.0),
            "environment":        env,
            "cpu_utilization":    safe_float(clean_row.get("cpu_utilization"), None),
            "memory_utilization": safe_float(clean_row.get("memory_utilization"), None),
        })
    if not resources:
        raise ValueError("No valid resources found in CSV")
    return resources


def parse_json(file_content: bytes) -> List[dict]:
    """Parse JSON bytes into a list of resource dicts."""
    data = json.loads(file_content.decode("utf-8-sig"))
    raw  = data if isinstance(data, list) else data.get("resources", [])
    resources = []
    for i, item in enumerate(raw):
        rtype    = clean(item.get("type", ""))
        provider = clean(item.get("provider", ""))
        if rtype not in VALID_TYPES or provider not in VALID_PROVIDERS:
            continue
        env = clean(item.get("environment", "production"))
        if env not in VALID_ENVS:
            env = "production"
        resources.append({
            "resource_name":      str(item.get("resource_name", f"resource_{i+1}")),
            "type":               rtype,
            "provider":           provider,
            "size":               str(item.get("size", "")).strip() or None,
            "storage_gb":         safe_float(item.get("storage_gb"), 0.0),
            "region":             str(item.get("region", "us-east-1")),
            "hours_per_day":      safe_float(item.get("hours_per_day"), 24.0),
            "environment":        env,
            "cpu_utilization":    safe_float(item.get("cpu_utilization"), None),
            "memory_utilization": safe_float(item.get("memory_utilization"), None),
        })
    if not resources:
        raise ValueError("No valid resources found in JSON")
    return resources


def validate_file_size(size_bytes: int) -> bool:
    """Check that file is within the 2MB limit."""
    return size_bytes <= 2 * 1024 * 1024
