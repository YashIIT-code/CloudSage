"""
CloudSage – File parser service.
Parses uploaded CSV / JSON files into CloudResource models using Pandas.
"""

import io
import json
import re
from typing import Any

import pandas as pd

from backend.models.schemas import CloudResource, Environment, Provider, ResourceType

# ─── Constants ───────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = {".csv", ".json"}

# Column alias mapping (lowercase) → CloudResource field
_ALIASES: dict[str, list[str]] = {
    "resource_id": ["id", "name", "resource", "instance", "resource_id", "resource_name", "instance_id"],
    "provider": ["provider", "cloud", "vendor", "platform"],
    "resource_type": ["type", "resource_type", "kind", "class", "category"],
    "region": ["region", "location", "zone", "datacenter", "availability_zone"],
    "instance_type": ["instance_type", "sku", "size", "family", "machine_type", "vm_size"],
    "environment": ["environment", "env", "stage", "tags", "tag", "label"],
    "cpu_utilization": ["cpu", "cpu_avg", "cpu_utilization", "cpu_usage", "compute"],
    "memory_utilization": ["mem", "memory", "mem_avg", "memory_utilization", "ram", "mem_usage"],
    "storage_gb": ["storage", "storage_gb", "disk", "volume", "gb", "disk_size"],
    "monthly_cost": ["cost", "monthly_cost", "spend", "price", "amount", "total", "monthly_spend"],
    "hours_per_day": ["hours", "hours_per_day", "hours_running", "runtime", "uptime", "hours_idle"],
    "tags": ["tags", "labels", "project"],
}


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", str(text))


def _resolve_column(columns: list[str], field: str) -> str | None:
    """Find the best matching column name for *field* using alias list."""
    aliases = _ALIASES.get(field, [])
    cols_lower = {c.lower().strip().replace(" ", "_"): c for c in columns}
    for alias in aliases:
        if alias in cols_lower:
            return cols_lower[alias]
    return None


def _parse_provider(val: Any) -> Provider:
    s = str(val).strip().lower()
    for p in Provider:
        if p.value in s:
            return p
    return Provider.aws


def _parse_environment(val: Any) -> Environment:
    s = str(val).strip().lower()
    if "dev" in s:
        return Environment.development
    if "stag" in s:
        return Environment.staging
    return Environment.production


def _parse_resource_type(val: Any) -> ResourceType:
    s = str(val).strip().lower()
    for rt in ResourceType:
        if rt.value in s:
            return rt
    # Heuristics
    if any(k in s for k in ("rds", "sql", "db", "postgres", "mysql", "mongo")):
        return ResourceType.database
    if any(k in s for k in ("s3", "blob", "gcs", "bucket", "disk")):
        return ResourceType.storage
    if any(k in s for k in ("ecs", "eks", "gke", "aks", "container", "pod", "docker")):
        return ResourceType.container
    return ResourceType.vm


def _safe_float(val: Any, default: Any = 0.0) -> Any:
    try:
        if pd.isna(val) or val == "" or str(val).strip() == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


# ─── Public API ──────────────────────────────────────────────────────────────────

def validate_file(filename: str, size: int) -> str | None:
    """Return an error string, or None if the file is valid."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    if size > MAX_FILE_SIZE:
        return f"File too large ({size / 1024 / 1024:.1f} MB). Maximum is 2 MB."
    return None


def parse_file(content: bytes, filename: str) -> list[CloudResource]:
    """Parse CSV or JSON bytes into a list of ``CloudResource``."""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext == ".json":
        return _parse_json(content)
    return _parse_csv(content)


def _parse_csv(content: bytes) -> list[CloudResource]:
    text = content.decode("utf-8-sig")
    df = pd.read_csv(io.StringIO(text))
    df.columns = df.columns.str.strip()
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    return _dataframe_to_resources(df)


def _parse_json(content: bytes) -> list[CloudResource]:
    data = json.loads(content.decode("utf-8"))
    if isinstance(data, dict):
        # Possibly wrapped: {"resources": [...]}
        for key in ("resources", "data", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            data = [data]
    df = pd.DataFrame(data)
    return _dataframe_to_resources(df)


def _dataframe_to_resources(df: pd.DataFrame) -> list[CloudResource]:
    resources: list[CloudResource] = []
    cols = list(df.columns)

    for _, row in df.iterrows():
        def _get(field: str, default: Any = None) -> Any:
            col = _resolve_column(cols, field)
            if col is not None and pd.notna(row.get(col)):
                return _strip_html(str(row[col]))
            return default

        resource_id = _get("resource_id", f"resource-{len(resources)}")
        provider = _parse_provider(_get("provider", "aws"))
        resource_type = _parse_resource_type(_get("resource_type", "vm"))
        region = _get("region", "us-east-1")
        instance_type = _get("instance_type", "t3.medium")
        environment = _parse_environment(_get("environment", "production"))
        cpu = _safe_float(_get("cpu_utilization", None), None)
        mem = _safe_float(_get("memory_utilization", None), None)
        storage = _safe_float(_get("storage_gb", 0.0), 0.0)
        cost = _safe_float(_get("monthly_cost", 0.0), 0.0)
        hours = _safe_float(_get("hours_per_day", 24.0), 24.0)
        tags = _get("tags", "")

        cpu_val = min(max(cpu, 0), 100) if cpu is not None else None
        mem_val = min(max(mem, 0), 100) if mem is not None else None

        resources.append(CloudResource(
            resource_id=resource_id,
            provider=provider,
            resource_type=resource_type,
            region=region,
            instance_type=instance_type,
            environment=environment,
            cpu_utilization=cpu_val,
            memory_utilization=mem_val,
            storage_gb=max(storage, 0),
            monthly_cost=max(cost, 0),
            hours_per_day=max(hours, 0),
            tags=tags,
        ))

    return resources
