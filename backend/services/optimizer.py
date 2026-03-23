"""
CloudSage Optimization Engine
==============================
Generates actionable cost-saving recommendations using rules-based logic
applied to the uploaded cost data and analysis results.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service classification keywords — used to categorise services and apply
# domain-specific optimisation rules.
# ---------------------------------------------------------------------------
COMPUTE_KEYWORDS = [
    'ec2', 'compute', 'vm', 'virtual machine', 'instance', 'lambda',
    'function', 'ecs', 'eks', 'fargate', 'container', 'batch',
]
STORAGE_KEYWORDS = [
    's3', 'storage', 'blob', 'ebs', 'disk', 'glacier', 'archive',
    'backup', 'snapshot',
]
DATABASE_KEYWORDS = [
    'rds', 'database', 'dynamodb', 'sql', 'cosmos', 'aurora',
    'redshift', 'elasticache', 'redis', 'mongo',
]
NETWORK_KEYWORDS = [
    'cloudfront', 'cdn', 'bandwidth', 'transfer', 'vpn', 'gateway',
    'load balancer', 'elb', 'alb', 'nlb', 'route53', 'dns',
]

# Thresholds for recommendations
HIGH_COST_PERCENTAGE = 30.0   # Service consuming > 30% of total
IDLE_USAGE_THRESHOLD = 1.0    # Usage below this is considered idle
SAVINGS_PCT_RESERVED = 15     # Estimated savings from reserved instances
SAVINGS_PCT_LIFECYCLE = 20    # Estimated savings from lifecycle policies
SAVINGS_PCT_RIGHTSIZE = 25    # Estimated savings from rightsizing


def generate_optimizations(cost_result: dict, analysis_result: dict) -> dict:
    """
    Generate cost optimization recommendations.

    Scans service breakdown and anomaly data to produce categorised,
    actionable recommendations with severity levels, estimated dollar
    savings, and a priority score.

    Args:
        cost_result: dict from cost_service.process_csv_content()
        analysis_result: dict from analyzer.analyze_costs()

    Returns:
        dict with total_potential_savings_pct, total_potential_savings_usd,
        and sorted recommendations list.
    """
    recommendations: list[dict] = []
    total_cost = cost_result.get("total_cost", 0.0)
    breakdown = cost_result.get("breakdown", [])
    service_breakdown = analysis_result.get("service_breakdown", {})
    anomalies = analysis_result.get("anomalies", [])

    if not breakdown or total_cost <= 0:
        return {
            "total_potential_savings_pct": 0,
            "total_potential_savings_usd": 0.0,
            "recommendations": []
        }

    # --- Analyse each service ---
    for svc, data in service_breakdown.items():
        svc_lower = svc.lower()
        cost = data.get("cost", 0)
        pct = data.get("percentage", 0)

        # 1. Compute rightsizing
        if _matches(svc_lower, COMPUTE_KEYWORDS):
            if pct > HIGH_COST_PERCENTAGE:
                savings_usd = cost * (SAVINGS_PCT_RIGHTSIZE / 100.0)
                recommendations.append({
                    "category": "rightsizing",
                    "severity": "high",
                    "service": svc,
                    "message": (
                        f"💡 {svc} accounts for {pct}% of your total cost (${cost:.2f}). "
                        f"Consider rightsizing to smaller instance types, using spot/preemptible "
                        f"instances, or enabling auto-scaling to reduce over-provisioning."
                    ),
                    "estimated_savings_pct": SAVINGS_PCT_RIGHTSIZE,
                    "estimated_savings_usd": round(savings_usd, 2),
                })
            elif pct > 10:
                savings_usd = cost * (10 / 100.0)
                recommendations.append({
                    "category": "rightsizing",
                    "severity": "medium",
                    "service": svc,
                    "message": (
                        f"🔍 Review {svc} utilization. If average CPU/Memory is < 40%, "
                        f"consider downsizing the instance family to save costs."
                    ),
                    "estimated_savings_pct": 10,
                    "estimated_savings_usd": round(savings_usd, 2),
                })

        # 2. Storage lifecycle policies
        if _matches(svc_lower, STORAGE_KEYWORDS):
            if pct > HIGH_COST_PERCENTAGE:
                savings_usd = cost * (SAVINGS_PCT_LIFECYCLE / 100.0)
                recommendations.append({
                    "category": "lifecycle_policy",
                    "severity": "high",
                    "service": svc,
                    "message": (
                        f"📦 {svc} storage is costing ${cost:.2f} ({pct}% of total). "
                        f"Implement lifecycle policies to automatically move data older than 30 or 90 days "
                        f"to cheaper cold tiers (e.g., S3 Glacier, Azure Cool Blob Storage, Deep Archive)."
                    ),
                    "estimated_savings_pct": SAVINGS_PCT_LIFECYCLE,
                    "estimated_savings_usd": round(savings_usd, 2),
                })
            else:
                savings_usd = cost * (5 / 100.0)
                recommendations.append({
                    "category": "lifecycle_policy",
                    "severity": "low",
                    "service": svc,
                    "message": (
                        f"📦 Consider enabling intelligent tiering for {svc} or defining a retention "
                        f"policy to automatically delete unused snapshots and backups."
                    ),
                    "estimated_savings_pct": 5,
                    "estimated_savings_usd": round(savings_usd, 2),
                })

        # 3. Database optimisation
        if _matches(svc_lower, DATABASE_KEYWORDS) and pct > 15:
            savings_usd = cost * (15 / 100.0)
            recommendations.append({
                "category": "database_optimization",
                "severity": "medium",
                "service": svc,
                "message": (
                    f"🗄️ Database spend on {svc} is significant (${cost:.2f}). Consider reserved DB instances, "
                    f"Serverless options (for spiky workloads), or pausing dev/test databases overnight."
                ),
                "estimated_savings_pct": 15,
                "estimated_savings_usd": round(savings_usd, 2),
            })

        # 4. Network cost review
        if _matches(svc_lower, NETWORK_KEYWORDS) and pct > 10:
            savings_usd = cost * (10 / 100.0)
            recommendations.append({
                "category": "network_optimization",
                "severity": "medium",
                "service": svc,
                "message": (
                    f"🌐 {svc} network costs are ${cost:.2f}. Review data transfer charges. "
                    f"Consider using VPC endpoints to avoid NAT Gateway charges, or implementing a CDN to reduce egress data."
                ),
                "estimated_savings_pct": 10,
                "estimated_savings_usd": round(savings_usd, 2),
            })

    # --- Idle resource detection ---
    idle_services = []
    for item in breakdown:
        if abs(item["usage"]) < IDLE_USAGE_THRESHOLD and item["cost"] > 0:
            idle_services.append((item["service"], item["cost"]))

    if idle_services:
        idle_services.sort(key=lambda x: x[1], reverse=True)
        unique_idle = list(dict.fromkeys([s[0] for s in idle_services]))[:5]
        idle_cost = sum(s[1] for s in idle_services[:5])
        
        recommendations.append({
            "category": "idle_resources",
            "severity": "high",
            "service": ", ".join(unique_idle),
            "message": (
                f"⚠️ Detected near-idle usage for: {', '.join(unique_idle)}. "
                f"Shutting down or de-provisioning these "
                f"resources could immediately save ${idle_cost:.2f}."
            ),
            "estimated_savings_pct": 100,  # relative to the item cost
            "estimated_savings_usd": round(idle_cost, 2),
        })

    # --- Repeated high-cost → reserved instances ---
    high_cost_services = [
        (svc, data.get("cost", 0)) for svc, data in service_breakdown.items()
        if data.get("percentage", 0) > 15 and _matches(svc.lower(), COMPUTE_KEYWORDS + DATABASE_KEYWORDS)
    ]
    if high_cost_services:
        services_str = ", ".join([s[0] for s in high_cost_services])
        combined_cost = sum(s[1] for s in high_cost_services)
        savings_usd = combined_cost * (SAVINGS_PCT_RESERVED / 100.0)
        
        recommendations.append({
            "category": "reserved_instances",
            "severity": "medium",
            "service": services_str,
            "message": (
                f"💰 Highly utilized compute/DB services: {services_str}. "
                f"If these workloads are steady, purchasing 1-year or 3-year Reserved Instances or Savings Plans "
                f"could yield ~$ {savings_usd:.2f} in savings."
            ),
            "estimated_savings_pct": SAVINGS_PCT_RESERVED,
            "estimated_savings_usd": round(savings_usd, 2),
        })

    # --- Flag anomalies ---
    for anomaly in anomalies:
        if anomaly["type"] == "cost_spike":
            sev = anomaly.get("severity", "high")
            recommendations.append({
                "category": "anomaly_review",
                "severity": sev,
                "service": anomaly.get("service", "all"),
                "message": (
                    f"🚨 {anomaly['detail']} Investigate the root cause immediately — "
                    f"this may indicate a misconfiguration, automated scaling error, or unexpected workload."
                ),
                "estimated_savings_pct": 0,
                "estimated_savings_usd": 0.0,
            })

    # --- General best practices (always included) ---
    recommendations.append({
        "category": "best_practice",
        "severity": "info",
        "service": "all",
        "message": (
            "📊 Enable a strict resource tagging strategy (e.g., Environment, Team, CostCenter). "
            "Set up AWS Budgets or Azure Cost Alerts to get notified before spend spirals out of control."
        ),
        "estimated_savings_pct": 0,
        "estimated_savings_usd": 0.0,
    })

    # --- Score and sort recommendations ---
    for rec in recommendations:
        rec["priority_score"] = _calculate_priority_score(rec, total_cost)

    # Sort by priority score (descending)
    recommendations.sort(key=lambda x: x["priority_score"], reverse=True)

    # --- Calculate total potential savings ---
    total_potential_pct = _estimate_total_savings_pct(recommendations, total_cost)
    total_potential_usd = sum(r.get("estimated_savings_usd", 0.0) for r in recommendations)
    
    # Cap total potential savings reasonably to avoid absurd projections
    total_potential_usd = min(total_potential_usd, total_cost * 0.5)

    logger.info(
        f"Optimisation complete — {len(recommendations)} recommendations, "
        f"potential savings: {total_potential_pct}% (~${total_potential_usd:.2f})"
    )

    return {
        "total_potential_savings_pct": total_potential_pct,
        "total_potential_savings_usd": round(total_potential_usd, 2),
        "recommendations": recommendations,
    }


def _matches(text: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the given text."""
    return any(kw in text for kw in keywords)


def _calculate_priority_score(rec: dict, total_cost: float) -> int:
    """
    Calculate a priority score (1-10) for a recommendation based on
    severity and potential dollar savings relative to total cost.
    """
    score = 1
    sev = rec.get("severity", "low")
    
    # Base score from severity
    if sev == "critical": score += 6
    elif sev == "high": score += 4
    elif sev == "medium": score += 2
    
    # Add points based on financial impact
    savings_usd = rec.get("estimated_savings_usd", 0.0)
    if total_cost > 0 and savings_usd > 0:
        impact_pct = savings_usd / total_cost
        if impact_pct > 0.10: score += 4
        elif impact_pct > 0.05: score += 2
        elif impact_pct > 0.01: score += 1
        
    return min(max(score, 1), 10)


def _estimate_total_savings_pct(recommendations: list[dict], total_cost: float) -> int:
    """
    Estimate an aggregate potential savings percentage from the
    recommendations (capped at a reasonable maximum).
    """
    if total_cost <= 0 or not recommendations:
        return 0

    # We sum the USD savings to get the total percentage, to avoid double counting
    total_savings_usd = sum(r.get("estimated_savings_usd", 0.0) for r in recommendations)
    
    if total_savings_usd == 0:
        return 0

    avg_savings_pct = (total_savings_usd / total_cost) * 100
    
    # Cap at 45% — being realistic for automated recommendations
    return min(int(round(avg_savings_pct)), 45)
