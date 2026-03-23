"""
CloudSage Forecasting Module
=============================
Predicts future cloud costs using linear regression, moving average,
or average-based extrapolation. Includes confidence intervals.
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def forecast_costs(cost_result: dict) -> dict:
    """
    Generate cost forecasts from calculation results.

    Strategy:
      1. If a date column was detected, aggregate daily costs.
      2. If enough data points (>7), use Moving Average, otherwise Linear Regression.
      3. Otherwise, use average cost per row as a proxy for daily cost
         and extrapolate.

    Args:
        cost_result: dict from cost_service.process_csv_content()

    Returns:
        dict with method, predicted costs, trend, daily average, and confidence intervals
    """
    df: pd.DataFrame | None = cost_result.get("_dataframe")
    date_col = cost_result.get("_date_col")
    total_cost = cost_result.get("total_cost", 0.0)
    breakdown = cost_result.get("breakdown", [])

    # --- Attempt time-series forecasting ---
    if df is not None and date_col and date_col in df.columns:
        result = _time_series_forecast(df, date_col)
        if result is not None:
            return result

    # --- Fallback: average-based extrapolation ---
    return _average_forecast(total_cost, len(breakdown))


def _time_series_forecast(df: pd.DataFrame, date_col: str) -> dict | None:
    """
    Fit a model on daily aggregated costs and predict forward.
    Uses Moving Average if >=7 days of data are available, 
    otherwise falls back to Linear Regression.
    """
    try:
        time_df = df.copy()
        time_df['__parsed_date'] = pd.to_datetime(
            time_df[date_col], errors='coerce'
        )
        time_df = time_df.dropna(subset=['__parsed_date'])

        if len(time_df) < 2:
            return None

        # Aggregate cost per day
        daily = (
            time_df.groupby('__parsed_date')['__computed_cost']
            .sum()
            .sort_index()
        )

        n_days = len(daily)
        if n_days < 2:
            return None

        y = daily.values.astype(float)
        daily_avg = float(np.mean(y))
        std_dev = float(np.std(y)) if n_days > 1 else 0.0

        method = "linear_regression"
        
        # Determine trend
        x = np.arange(n_days, dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        trend = _classify_trend(slope, daily_avg)

        if n_days >= 7:
            # Use 7-day Moving Average for predictions if we have enough data
            method = "moving_average_7d"
            ma_val = np.mean(y[-7:])
            pred_7 = ma_val * 7
            pred_30 = ma_val * 30
        else:
            # Use Linear Regression
            last_idx = n_days - 1
            pred_7 = sum(slope * (last_idx + i) + intercept for i in range(1, 8))
            pred_30 = sum(slope * (last_idx + i) + intercept for i in range(1, 31))

        # Ensure predictions are non-negative
        pred_7 = max(float(pred_7), 0.0)
        pred_30 = max(float(pred_30), 0.0)
        
        # Calculate naive confidence intervals (±1 standard deviation of the daily history, scaled up)
        # Bounded at 0 for the lower bound.
        ci_lower_7 = max(0.0, float(pred_7 - (std_dev * 2.64))) # sqrt(7) approximations
        ci_upper_7 = float(pred_7 + (std_dev * 2.64))
        
        ci_lower_30 = max(0.0, float(pred_30 - (std_dev * 5.47))) # sqrt(30)
        ci_upper_30 = float(pred_30 + (std_dev * 5.47))

        logger.info(
            f"Time-series forecast ({method}) — n_days: {n_days}, "
            f"daily_avg: {daily_avg:.2f}, trend: {trend}"
        )

        return {
            "method": method,
            "data_points_used": n_days,
            "predicted_cost_next_7_days": round(pred_7, 2),
            "predicted_cost_next_30_days": round(pred_30, 2),
            "confidence_interval_7d": {"lower": round(ci_lower_7, 2), "upper": round(ci_upper_7, 2)},
            "confidence_interval_30d": {"lower": round(ci_lower_30, 2), "upper": round(ci_upper_30, 2)},
            "trend": trend,
            "daily_average_cost": round(daily_avg, 2),
        }
    except Exception as e:
        logger.warning(f"Time-series forecasting failed: {e}")
        return None


def _average_forecast(total_cost: float, row_count: int) -> dict:
    """
    When no time column is available, estimate future cost by treating
    each row as roughly one "unit" of daily activity.
    """
    if row_count <= 0:
        daily_avg = 0.0
    else:
        daily_avg = total_cost / max(row_count, 1)

    pred_7 = round(daily_avg * 7, 2)
    pred_30 = round(daily_avg * 30, 2)
    
    # Simple bounds for average extrapolation (±20%)
    margin_7 = pred_7 * 0.2
    margin_30 = pred_30 * 0.2

    logger.info(
        f"Average-based forecast — daily_avg: {daily_avg:.2f}, "
        f"7d: {pred_7:.2f}, 30d: {pred_30:.2f}"
    )

    return {
        "method": "average_extrapolation",
        "data_points_used": row_count,
        "predicted_cost_next_7_days": pred_7,
        "predicted_cost_next_30_days": pred_30,
        "confidence_interval_7d": {"lower": max(0, round(pred_7 - margin_7, 2)), "upper": round(pred_7 + margin_7, 2)},
        "confidence_interval_30d": {"lower": max(0, round(pred_30 - margin_30, 2)), "upper": round(pred_30 + margin_30, 2)},
        "trend": "stable",
        "daily_average_cost": round(daily_avg, 2),
    }


def _classify_trend(slope: float, daily_avg: float) -> str:
    """
    Classify the cost trend based on the regression slope relative to
    the daily average cost.

    - |slope| < 5% of daily average  → "stable"
    - slope > 0                      → "increasing"
    - slope < 0                      → "decreasing"
    """
    if daily_avg == 0:
        return "stable"
    ratio = abs(slope) / daily_avg
    if ratio < 0.05:
        return "stable"
    return "increasing" if slope > 0 else "decreasing"
