"""
CloudSage Inefficiency Detector
================================
8 rule-based detections using pure Python math.
No AI — just deterministic pattern matching.
"""
from typing import List


def detect_inefficiencies(resources, costs) -> list:
    """Detect cost inefficiencies across resources using 8 rules."""
    results = []
    for resource, cost in zip(resources, costs):
        env   = str(resource.environment).lower().replace("environment.", "")
        rtype = str(resource.type).lower().replace("resourcetype.", "")
        size  = str(resource.size or "").lower()
        hours = float(resource.hours_per_day or 24)
        cpu   = resource.cpu_utilization
        mem   = resource.memory_utilization
        gb    = float(resource.storage_gb or 0)

        # RULE 1: Dev/staging 24/7
        if env in ("development", "staging") and hours >= 24:
            results.append({
                "resource_name": resource.resource_name,
                "issue": "Dev/staging running 24/7. Enable auto-shutdown to save 65%.",
                "severity": "high",
                "potential_saving": round(cost * 0.65, 2),
            })

        # RULE 2: CPU underutilization
        if cpu is not None and cpu < 20:
            results.append({
                "resource_name": resource.resource_name,
                "issue": f"CPU only {cpu}%. Resource oversized. Downsize to save 50%.",
                "severity": "high",
                "potential_saving": round(cost * 0.50, 2),
            })

        # RULE 3: Memory underutilization
        if mem is not None and mem < 25:
            results.append({
                "resource_name": resource.resource_name,
                "issue": f"Memory only {mem}%. Consider downsizing.",
                "severity": "medium",
                "potential_saving": round(cost * 0.30, 2),
            })

        # RULE 4: Large hot storage
        if rtype == "storage" and gb > 100:
            results.append({
                "resource_name": resource.resource_name,
                "issue": f"Large storage ({gb}GB) on hot tier. Move to cool tier to save 44%.",
                "severity": "medium",
                "potential_saving": round(cost * 0.44, 2),
            })

        # RULE 5: Oversized VM
        if rtype == "vm" and any(
            k in size
            for k in ["d8s", "d16s", "m5.2xlarge", "n1-standard-8", "r5.xlarge", "e4s"]
        ):
            results.append({
                "resource_name": resource.resource_name,
                "issue": "Large VM detected. Verify full capacity is needed.",
                "severity": "medium",
                "potential_saving": round(cost * 0.40, 2),
            })

        # RULE 6: Database in dev
        if rtype == "database" and env == "development":
            results.append({
                "resource_name": resource.resource_name,
                "issue": "Dedicated DB in dev env. Use shared dev DB to save 80%.",
                "severity": "high",
                "potential_saving": round(cost * 0.80, 2),
            })

        # RULE 7: No reserved instances
        if rtype == "vm" and env == "production" and hours >= 24:
            results.append({
                "resource_name": resource.resource_name,
                "issue": "24/7 production VM not on reserved pricing. Save 30-40%.",
                "severity": "low",
                "potential_saving": round(cost * 0.35, 2),
            })

        # RULE 8: Premium database
        if rtype == "database" and any(
            k in size for k in ["premium", "m5.xlarge", "db-n1-standard-4"]
        ):
            results.append({
                "resource_name": resource.resource_name,
                "issue": "Premium DB tier. Verify performance requirements.",
                "severity": "low",
                "potential_saving": round(cost * 0.25, 2),
            })

    return results


def calculate_efficiency_score(inefficiencies: list) -> int:
    """Calculate efficiency score (0-100) based on severity penalties."""
    score = 100
    for i in inefficiencies:
        sev = i.severity if hasattr(i, "severity") else i.get("severity", "")
        if sev == "high":
            score -= 20
        elif sev == "medium":
            score -= 10
        elif sev == "low":
            score -= 5
    return max(0, score)
