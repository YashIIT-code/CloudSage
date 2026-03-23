"""
CloudSage Cost Analysis Module
==============================
Generates insights from uploaded cost data: service breakdown with
percentages, top services, cost velocity, and anomaly detection.
"""

import logging
import pandas as pd
from typing import Any

logger = logging.getLogger(__name__)


def analyze_costs(cost_result: dict) -> dict:
    """
    Analyse the cost calculation results and produce actionable insights.

    Args:
        cost_result: The dict returned by cost_service.process_csv_content()

    Returns:
        dict with total_cost, cost_velocity, service_breakdown, top_services, anomalies
    """
    breakdown = cost_result.get("breakdown", [])
    total_cost = cost_result.get("total_cost", 0.0)
    df: pd.DataFrame | None = cost_result.get("_dataframe")
    date_col = cost_result.get("_date_col")

    if not breakdown:
        return _empty_analysis(total_cost)

    # ------------------------------------------------------------------
    # 1. Service breakdown with cost & percentage contribution
    # ------------------------------------------------------------------
    service_costs: dict[str, float] = {}
    for item in breakdown:
        svc = item["service"]
        service_costs[svc] = service_costs.get(svc, 0.0) + item["cost"]

    service_breakdown = {}
    for svc, cost in service_costs.items():
        pct = round((cost / total_cost) * 100, 2) if total_cost else 0.0
        service_breakdown[svc] = {"cost": round(cost, 2), "percentage": pct}

    # ------------------------------------------------------------------
    # 2. Top 5 most expensive services
    # ------------------------------------------------------------------
    sorted_services = sorted(
        service_breakdown.items(), key=lambda x: x[1]["cost"], reverse=True
    )
    top_services = [
        {"service": svc, "cost": data["cost"], "percentage": data["percentage"]}
        for svc, data in sorted_services[:5]
    ]

    # ------------------------------------------------------------------
    # 3. Cost Velocity & Aggregation
    # ------------------------------------------------------------------
    cost_velocity = "Unknown"
    if df is not None and date_col and date_col in df.columns:
        try:
            time_df = df.copy()
            time_df['__parsed_date'] = pd.to_datetime(
                time_df[date_col], errors='coerce'
            )
            time_df = time_df.dropna(subset=['__parsed_date'])
            if len(time_df) > 1:
                dayspan = (time_df['__parsed_date'].max() - time_df['__parsed_date'].min()).days
                if dayspan > 0:
                    velocity = total_cost / dayspan
                    cost_velocity = f"${velocity:.2f} / day"
        except Exception as e:
            logger.debug(f"Could not calculate cost velocity: {e}")

    # ------------------------------------------------------------------
    # 4. Anomaly detection
    # ------------------------------------------------------------------
    anomalies = _detect_anomalies(breakdown, df, date_col, service_costs, total_cost)

    logger.info(
        f"Analysis complete — {len(service_breakdown)} services, "
        f"{len(anomalies)} anomalies detected. Velocity: {cost_velocity}"
    )

    return {
        "total_cost": total_cost,
        "cost_velocity": cost_velocity,
        "service_count": len(service_breakdown),
        "service_breakdown": service_breakdown,
        "top_services": top_services,
        "anomalies": anomalies,
    }


def _detect_anomalies(
    breakdown: list[dict],
    df: pd.DataFrame | None,
    date_col: str | None,
    service_costs: dict[str, float],
    total_cost: float,
) -> list[dict[str, Any]]:
    """
    Detect cost anomalies:
      - Unusually high usage rows  (usage > mean + 2 * std)
      - Services consuming > 50% of budget
      - Time-based spikes if date column is available
    """
    anomalies: list[dict[str, Any]] = []

    # --- High-usage rows (statistical outlier) ---
    if df is not None and '__usage_num' in df.columns:
        usage_series = df['__usage_num'].dropna()
        if len(usage_series) > 5:  # Need minimum data for valid statistical mean
            mean_usage = usage_series.mean()
            std_usage = usage_series.std()
            # If standard deviation is 0, all usage is the same; ignore
            if std_usage > 0:
                threshold = mean_usage + (3 * std_usage) # increased to 3 std dev to reduce noise
                outliers = df[df['__usage_num'] > threshold]
                for _, row in outliers.iterrows():
                    svc = row.get('__service', 'Unknown')
                    row_cost = row.get('__computed_cost', 0)
                    pct_impact = round((row_cost / total_cost) * 100, 1) if total_cost > 0 else 0
                    
                    if pct_impact > 1.0: # Only report if it actually impacted the bill > 1%
                        anomalies.append({
                            "type": "high_usage",
                            "severity": "medium",
                            "service": str(svc),
                            "impact_pct": pct_impact,
                            "detail": (
                                f"Usage chunk of {row['__usage_num']:.2f} is significantly above "
                                f"average ({mean_usage:.2f}), impacting {pct_impact}% of total bill."
                            ),
                        })

    # --- Dominant service (> 50% of total cost) ---
    for svc, cost in service_costs.items():
        if total_cost > 0 and (cost / total_cost) > 0.50:
            pct = round((cost / total_cost) * 100, 1)
            anomalies.append({
                "type": "cost_concentration",
                "severity": "high" if pct > 75 else "medium",
                "service": svc,
                "impact_pct": pct,
                "detail": (
                    f"{svc} accounts for {pct}% of total spend (${cost:.2f}). "
                    f"Consider diversifying or negotiating pricing."
                ),
            })

    # --- Time-based spike detection ---
    if df is not None and date_col and date_col in df.columns:
        try:
            time_df = df.copy()
            time_df['__parsed_date'] = pd.to_datetime(
                time_df[date_col], errors='coerce'
            )
            time_df = time_df.dropna(subset=['__parsed_date'])
            if len(time_df) >= 2:
                daily = (
                    time_df.groupby('__parsed_date')['__computed_cost']
                    .sum()
                    .sort_index()
                )
                if len(daily) >= 3:
                    pct_change = daily.pct_change().dropna()
                    # Look for jumps strictly > 100% (double the cost)
                    spikes = pct_change[pct_change > 1.0]
                    for date, change_val in spikes.items():
                        cost_on_date = daily.loc[date]
                        impact_pct = round((cost_on_date / total_cost) * 100, 1) if total_cost > 0 else 0
                        anomalies.append({
                            "type": "cost_spike",
                            "severity": "critical" if change_val > 5.0 else "high",
                            "service": "all",
                            "impact_pct": impact_pct,
                            "detail": (
                                f"Cost spiked {change_val * 100:.0f}% on "
                                f"{date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else date}."
                            ),
                        })
        except Exception as e:
            logger.warning(f"Time-based anomaly detection failed: {e}")

    # Sort anomalies by severity (critical > high > medium > low)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    anomalies.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

    return anomalies


def _empty_analysis(total_cost: float) -> dict:
    """Return an empty analysis result when no data is available."""
    return {
        "total_cost": total_cost,
        "cost_velocity": "Unknown",
        "service_count": 0,
        "service_breakdown": {},
        "top_services": [],
        "anomalies": [],
    }
