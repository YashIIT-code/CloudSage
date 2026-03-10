"""
CloudSage – Inefficiency detection engine.
Applies 8 rules against each resource and computes an efficiency score.
"""

from backend.models.schemas import (
    CloudResource,
    Environment,
    Inefficiency,
    ResourceType,
)
from backend.services.pricing import calculate_resource_cost


# ─── Detection rules ────────────────────────────────────────────────────────────

def detect_inefficiencies(resource: CloudResource) -> list[Inefficiency]:
    """Run all 8 rules against *resource* and return matching ``Inefficiency`` items."""
    issues: list[Inefficiency] = []
    cost = calculate_resource_cost(resource)
    rid = resource.resource_id

    # Rule 1 – Dev/staging running 24/7
    if (
        resource.environment in (Environment.development, Environment.staging)
        and resource.hours_per_day >= 23
    ):
        issues.append(Inefficiency(
            rule_id="DEV_247",
            issue=f"{rid}: Dev/staging resource running 24/7 without auto-shutdown schedule",
            severity="High",
            estimated_saving=round(cost * 0.65, 2),
            resource_id=rid,
        ))

    # Rule 2 – CPU utilisation < 20 %
    if resource.cpu_utilization is not None and resource.cpu_utilization < 20:
        issues.append(Inefficiency(
            rule_id="LOW_CPU",
            issue=f"{rid}: CPU utilisation critically low at {resource.cpu_utilization:.0f}% — resource is oversized",
            severity="High",
            estimated_saving=round(cost * 0.50, 2),
            resource_id=rid,
        ))

    # Rule 3 – Memory utilisation < 25 %
    if resource.memory_utilization is not None and resource.memory_utilization < 25:
        issues.append(Inefficiency(
            rule_id="LOW_MEM",
            issue=f"{rid}: Memory utilisation low at {resource.memory_utilization:.0f}% — consider rightsizing",
            severity="Medium",
            estimated_saving=round(cost * 0.30, 2),
            resource_id=rid,
        ))

    # Rule 4 – Large hot storage > 100 GB
    if resource.resource_type == ResourceType.storage and resource.storage_gb > 100:
        issues.append(Inefficiency(
            rule_id="LARGE_HOT_STORAGE",
            issue=f"{rid}: {resource.storage_gb:.0f} GB on hot storage tier — migrate cold data to archive",
            severity="Medium",
            estimated_saving=round(cost * 0.44, 2),
            resource_id=rid,
        ))

    # Rule 5 – Oversized VM types
    oversized_types = {
        "d8s", "d8s_v3", "standard_d8s_v3",
        "m5.2xlarge", "m5.4xlarge",
        "r5.2xlarge", "r5.4xlarge",
        "n1-highmem-8", "n2-highmem-8",
        "p3.2xlarge", "p3.8xlarge",
    }
    if resource.instance_type.lower().replace(" ", "") in oversized_types:
        issues.append(Inefficiency(
            rule_id="OVERSIZED_VM",
            issue=f"{rid}: Instance type {resource.instance_type} is oversized for current utilisation",
            severity="Medium",
            estimated_saving=round(cost * 0.40, 2),
            resource_id=rid,
        ))

    # Rule 6 – Dev/staging database
    if (
        resource.resource_type == ResourceType.database
        and resource.environment in (Environment.development, Environment.staging)
    ):
        issues.append(Inefficiency(
            rule_id="DEV_DB",
            issue=f"{rid}: Full database running in {resource.environment.value} — use serverless or scaled-down tier",
            severity="High",
            estimated_saving=round(cost * 0.80, 2),
            resource_id=rid,
        ))

    # Rule 7 – No reserved instances (heuristic: production VM running 24/7 w/o RI tag)
    if (
        resource.resource_type == ResourceType.vm
        and resource.environment == Environment.production
        and resource.hours_per_day >= 23
        and "reserved" not in resource.tags.lower()
        and "ri" not in resource.tags.lower()
    ):
        issues.append(Inefficiency(
            rule_id="NO_RI",
            issue=f"{rid}: Production VM running 24/7 without Reserved Instance commitment",
            severity="Low",
            estimated_saving=round(cost * 0.35, 2),
            resource_id=rid,
        ))

    # Rule 8 – Premium database tier
    premium_keywords = ("premium", "business_critical", "businesscritical", "memory_optimized")
    if resource.resource_type == ResourceType.database and any(
        kw in resource.instance_type.lower() for kw in premium_keywords
    ):
        issues.append(Inefficiency(
            rule_id="PREMIUM_DB",
            issue=f"{rid}: Running on premium database tier — evaluate if General Purpose is sufficient",
            severity="Low",
            estimated_saving=round(cost * 0.25, 2),
            resource_id=rid,
        ))

    return issues


# ─── Efficiency score ────────────────────────────────────────────────────────────

def calculate_efficiency_score(inefficiencies: list[Inefficiency]) -> int:
    """
    Score = 100 − (High × 20) − (Medium × 10) − (Low × 5).
    Clamped to [0, 100].
    """
    high = sum(1 for i in inefficiencies if i.severity == "High")
    med = sum(1 for i in inefficiencies if i.severity == "Medium")
    low = sum(1 for i in inefficiencies if i.severity == "Low")

    score = 100 - (high * 20) - (med * 10) - (low * 5)
    return max(0, min(100, score))
