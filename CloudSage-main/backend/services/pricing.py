import logging
from backend.models.schemas import CloudResource, Environment, Provider, ResourceType

logger = logging.getLogger("cloudsage")

PRICING: dict[str, dict[str, float]] = {
    "aws": {
        "vm": 150.0,
        "database": 350.0,
        "container": 75.0,
    },
    "azure": {
        "vm": 145.0,
        "standard_d4s_v3": 140.16,
        "standard_d2s_v3": 70.08,
        "database": 340.0,
        "container": 70.0,
    },
    "gcp": {
        "vm": 140.0,
        "database": 330.0,
        "container": 68.0,
    },
}

FALLBACKS = {
    ("vm", "azure"): 70.08,
    ("vm", "aws"): 70.08,
    ("vm", "gcp"): 69.35,
    ("database", "azure"): 150.08,
    ("database", "aws"): 138.70,
    ("database", "gcp"): 92.98,
}

def calculate_resource_cost(resource: CloudResource) -> float:
    if resource.monthly_cost > 0:
        return resource.monthly_cost

    provider_key = resource.provider.value.lower()
    type_key = resource.resource_type.value.lower()
    size_key = resource.instance_type.strip().lower()

    if type_key == "storage":
        base = 0.02
        return round(resource.storage_gb * base, 2)
    elif type_key == "container":
        base = 50.0
    else:
        # Check size directly in our current simple dict if applicable, else fallback
        base = PRICING.get(provider_key, {}).get(size_key)
        if base is None:
            base = FALLBACKS.get((type_key, provider_key), 50.0)
            logger.warning(f"Fallback used for {provider_key} {type_key} size {size_key}: {base}")

    hours = float(resource.hours_per_day)
    if hours == 0:
        hours = 24.0

    return round(base * (hours / 24.0), 2)

def get_optimized_cost(resource: CloudResource) -> float:
    current = calculate_resource_cost(resource)
    if current == 0:
        return 0.0

    reduction = 0.0

    if resource.environment in (Environment.development, Environment.staging) and float(resource.hours_per_day) >= 23:
        reduction = max(reduction, 0.65)

    if resource.resource_type == ResourceType.storage and resource.storage_gb > 100:
        reduction = max(reduction, 0.44)

    if reduction == 0.0:
        reduction = 0.25  # 25% default saving assumption

    optimized = round(current * (1 - reduction), 2)
    
    if optimized > current:
        optimized = current
    if optimized == 0:
        optimized = 0.01

    return optimized
