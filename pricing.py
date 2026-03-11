import logging
import re
from typing import Any
from models import CloudResource, Environment, Provider, ResourceType

logger = logging.getLogger("cloudsage")

PRICING = {
    "azure": {
        "vm": {
            "standard_b1s": 7.59,
            "standard_b2s": 30.37,
            "standard_b4ms": 60.74,
            "standard_d2s_v3": 70.08,
            "standard_d4s_v3": 140.16,
            "standard_d8s_v3": 280.32,
            "standard_d16s_v3": 560.64,
            "standard_f2s": 61.32,
            "standard_f4s": 122.64,
            "standard_e2s_v3": 91.98,
            "standard_e4s_v3": 183.96,
        },
        "storage": {
            "hot": 0.018,
            "cool": 0.010,
            "archive": 0.00099,
        },
        "database": {
            "basic": 4.90,
            "standard_s0": 14.72,
            "standard_s1": 29.44,
            "standard_s2": 150.08,
            "standard_s3": 300.16,
            "premium_p1": 465.56,
            "premium_p2": 931.12,
        },
        "container": {"default": 50.00},
    },
    "aws": {
        "vm": {
            "t3.nano": 3.80,
            "t3.micro": 7.59,
            "t3.small": 15.18,
            "t3.medium": 30.37,
            "t3.large": 60.74,
            "t3.xlarge": 121.48,
            "t3.2xlarge": 242.96,
            "m5.large": 70.08,
            "m5.xlarge": 140.16,
            "m5.2xlarge": 280.32,
            "m5.4xlarge": 560.64,
            "c5.large": 61.20,
            "c5.xlarge": 122.40,
            "c5.2xlarge": 244.80,
            "r5.large": 90.96,
            "r5.xlarge": 181.92,
            "r5.2xlarge": 363.84,
            "p3.2xlarge": 2235.00,
        },
        "storage": {
            "standard": 0.023,
            "infrequent": 0.0125,
            "glacier": 0.004,
        },
        "database": {
            "db.t3.micro": 12.41,
            "db.t3.small": 24.82,
            "db.t3.medium": 49.64,
            "db.m5.large": 138.70,
            "db.m5.xlarge": 277.40,
            "m0": 0.00, "m10": 57.00, "m20": 113.00, "m30": 226.00,
        },
        "container": {"default": 73.00},
    },
    "gcp": {
        "vm": {
            "e2-micro": 6.11,
            "e2-small": 12.26,
            "e2-medium": 24.53,
            "e2-standard-2": 48.91,
            "n1-standard-1": 34.67,
            "n1-standard-2": 69.35,
            "n1-standard-4": 138.70,
            "n1-standard-8": 277.40,
            "n1-highmem-4": 182.50,
            "c2-standard-4": 138.18,
            "n2-standard-2": 77.93,
            "n2-standard-4": 155.86,
        },
        "storage": {
            "standard": 0.020,
            "nearline": 0.010,
            "coldline": 0.004,
            "archive": 0.0012,
        },
        "database": {
            "db-f1-micro": 7.67,
            "db-g1-small": 25.56,
            "db-n1-standard-1": 46.49,
            "db-n1-standard-2": 92.98,
            "db-n1-standard-4": 185.95,
        },
        "container": {"default": 73.00},
    },
}

FALLBACK_PRICES = {
    "azure": {"vm": 70.08, "storage": 0.018, "database": 150.08, "container": 50.00},
    "aws":   {"vm": 70.08, "storage": 0.023, "database": 138.70, "container": 73.00},
    "gcp":   {"vm": 69.35, "storage": 0.020, "database": 92.98,  "container": 73.00},
}

def normalize(text) -> str:
    if not text:
        return ""
    val = text.value if hasattr(text, 'value') else text
    return str(val).strip().lower()

def calculate_resource_cost(resource: CloudResource) -> float:
    # If cost is already provided and valid, prioritize it!
    # Explicitly check for Pydantic field access
    rc_cost = getattr(resource, 'monthly_cost', 0.0)
    if rc_cost and rc_cost > 0:
        return round(float(rc_cost), 2)

    provider = normalize(resource.provider)
    rtype = normalize(resource.type)
    size = normalize(resource.size)
    hours = float(resource.hours_per_day or 24)
    if hours <= 0:
        hours = 24.0
    hours_ratio = hours / 24.0

    provider_prices = PRICING.get(provider, {})
    type_prices = provider_prices.get(rtype, {})

    if rtype == "storage":
        storage_gb = float(resource.storage_gb or 100.0)
        price_per_gb = type_prices.get(size)
        if price_per_gb is None:
            price_per_gb = next(iter(type_prices.values()), None)
        if price_per_gb is None:
            price_per_gb = FALLBACK_PRICES.get(provider, {}).get(rtype, 0.02)
        return round(storage_gb * price_per_gb, 2)

    base_price = type_prices.get(size)
    if base_price is None and isinstance(type_prices, dict):
        for key, val in type_prices.items():
            if size in key or key in size:
                base_price = val
                break
    
    if base_price is None:
        base_price = FALLBACK_PRICES.get(provider, {}).get(rtype, 50.0)
        logger.warning(f"Fallback used for {provider} {rtype} size {size}: {base_price}")

    return round(base_price * hours_ratio, 2)

def get_optimized_cost(resource: CloudResource, current_cost: float) -> tuple:
    if current_cost <= 0:
        return (0.0, "No cost to optimize")

    env = normalize(resource.environment)
    rtype = normalize(resource.type)
    hours = float(resource.hours_per_day or 24)

    reduction = 0.0
    reason = "General optimization potential"

    if env in ("development", "staging") and hours >= 23:
        reduction = 0.65
        reason = "Auto-shutdown saves 65%"

    if rtype == "storage" and resource.storage_gb > 100:
        if 0.44 > reduction:
            reduction = 0.44
            reason = "Move to cool/infrequent tier"

    if resource.cpu_utilization is not None and resource.cpu_utilization < 20:
        if 0.50 > reduction:
            reduction = 0.50
            reason = "Downsize VM - CPU under 20%"

    if reduction == 0.0:
        reduction = 0.25

    optimized = round(current_cost * (1 - reduction), 2)
    return (max(0.01, min(optimized, current_cost)), reason)
