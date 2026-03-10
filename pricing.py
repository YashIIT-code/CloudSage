"""
CloudSage Pricing Engine
========================
Pure Python math — no AI involved.
Contains full pricing tables for Azure, AWS, GCP across VM, Storage, Database, Container.
"""

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
            "t3.micro": 7.59,
            "t3.small": 15.18,
            "t3.medium": 30.37,
            "t3.large": 60.74,
            "m5.large": 70.08,
            "m5.xlarge": 140.16,
            "m5.2xlarge": 280.32,
            "c5.large": 61.20,
            "c5.xlarge": 122.40,
            "r5.large": 90.96,
            "r5.xlarge": 181.92,
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
            "n1-standard-2": 69.35,
            "n1-standard-4": 138.70,
            "n1-standard-8": 277.40,
            "c2-standard-4": 138.18,
            "n2-standard-2": 77.93,
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

DOWNGRADE_MAP = {
    "azure": {
        "vm": {
            "standard_d16s_v3": "Standard_D8s_v3",
            "standard_d8s_v3":  "Standard_D4s_v3",
            "standard_d4s_v3":  "Standard_D2s_v3",
            "standard_d2s_v3":  "Standard_B2s",
            "standard_e4s_v3":  "Standard_D4s_v3",
            "standard_f4s":     "Standard_F2s",
        },
        "database": {
            "premium_p2": "Premium_P1", "premium_p1": "Standard_S3",
            "standard_s3": "Standard_S2", "standard_s2": "Standard_S1",
            "standard_s1": "Standard_S0",
        },
    },
    "aws": {
        "vm": {
            "m5.2xlarge": "m5.xlarge", "m5.xlarge": "m5.large",
            "m5.large": "t3.large",    "t3.large": "t3.medium",
            "t3.medium": "t3.small",   "r5.xlarge": "r5.large",
            "c5.xlarge": "c5.large",
        },
        "database": {
            "db.m5.xlarge": "db.m5.large", "db.m5.large": "db.t3.medium",
            "db.t3.medium": "db.t3.small", "db.t3.small": "db.t3.micro",
        },
    },
    "gcp": {
        "vm": {
            "n1-standard-8": "n1-standard-4", "n1-standard-4": "n1-standard-2",
            "n1-standard-2": "e2-standard-2", "e2-standard-2": "e2-medium",
            "c2-standard-4": "n1-standard-4",
        },
    },
}


def normalize(text) -> str:
    """Normalize a string for lookup: strip whitespace, lowercase. Handles Enums."""
    if not text:
        return ""
    # Extract .value from Pydantic/Python enums
    val = text.value if hasattr(text, 'value') else text
    return str(val).strip().lower()


def calculate_resource_cost(resource) -> float:
    """Calculate the monthly cost for a single resource using the pricing tables."""
    provider    = normalize(resource.provider)
    rtype       = normalize(resource.type)
    size        = normalize(resource.size or "")
    hours       = float(resource.hours_per_day or 24)
    if hours <= 0:
        hours = 24.0
    hours_ratio = hours / 24.0

    provider_prices = PRICING.get(provider, {})
    type_prices     = provider_prices.get(rtype, {})

    # Storage: flat per-GB per-month, no hours multiplier
    if rtype == "storage":
        storage_gb   = float(resource.storage_gb or 100.0)
        price_per_gb = type_prices.get(size)
        if price_per_gb is None:
            price_per_gb = next(iter(type_prices.values()), None)
        if price_per_gb is None:
            price_per_gb = FALLBACK_PRICES.get(provider, {}).get(rtype, 0.02)
        return round(storage_gb * price_per_gb, 2)

    # VM / Database / Container
    base_price = type_prices.get(size)
    if base_price is None:
        for key, val in type_prices.items():
            if size in key or key in size:
                base_price = val
                break
    if base_price is None:
        base_price = FALLBACK_PRICES.get(provider, {}).get(rtype, 50.0)

    return round(base_price * hours_ratio, 2)


def get_optimized_cost(resource, current_cost: float) -> tuple:
    """Calculate the optimized cost and reason for a single resource."""
    if current_cost <= 0:
        return (0.0, "No cost to optimize")

    provider = normalize(resource.provider)
    rtype    = normalize(resource.type)
    size     = normalize(resource.size or "")
    env      = normalize(resource.environment)
    hours    = float(resource.hours_per_day or 24)

    # Rule 1: Dev/staging 24/7
    if env in ("development", "staging") and hours >= 24:
        return (round(current_cost * 0.35, 2), "Auto-shutdown saves 65%")

    # Rule 2: Low CPU
    if resource.cpu_utilization is not None and resource.cpu_utilization < 20:
        return (round(current_cost * 0.50, 2), "Downsize VM - CPU under 20%")

    # Rule 3: Large hot storage
    if rtype == "storage" and (resource.storage_gb or 0) > 100:
        return (round(current_cost * 0.56, 2), "Move to cool/infrequent tier")

    # Rule 4: Downgrade map
    provider_map = DOWNGRADE_MAP.get(provider, {})
    type_map     = provider_map.get(rtype, {})
    downgrade_to = type_map.get(size)
    if downgrade_to:
        type_prices = PRICING.get(provider, {}).get(rtype, {})
        new_price   = type_prices.get(normalize(downgrade_to))
        if new_price:
            optimized = round(new_price * (hours / 24.0), 2)
            if optimized < current_cost:
                return (optimized, f"Downgrade to {downgrade_to}")

    # Default: 25% saving
    return (round(current_cost * 0.75, 2), "General optimization potential")
