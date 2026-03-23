"""
Integration tests for the full CloudSage pipeline.
Ensures cost_service, analyzer, forecaster, and optimizer
work together seamlessly with a realistic CSV.
"""
import os
import pytest
from services.cost_service import process_csv_content
from services.analyzer import analyze_costs
from services.forecaster import forecast_costs
from services.optimizer import generate_optimizations


@pytest.fixture
def sample_csv_path():
    return os.path.join(os.path.dirname(__file__), "sample_cloud_costs.csv")


def test_full_pipeline(sample_csv_path):
    with open(sample_csv_path, "rb") as f:
        content = f.read()

    # 1. Cost Calculation
    calc_result = process_csv_content(content)
    assert calc_result["total_cost"] > 0
    assert "date" in calc_result["detected_columns"]
    assert "region" in list(calc_result["detected_columns"].keys())
    assert "_dataframe" in calc_result

    # 2. Analysis
    analysis = analyze_costs(calc_result)
    assert analysis["total_cost"] == calc_result["total_cost"]
    assert len(analysis["service_breakdown"]) == 4 # EC2, RDS, S3, CloudTrail
    assert "anomalies" in analysis
    # We expect a spike anomaly on March 6/7 for CloudTrail or EC2
    assert len(analysis["anomalies"]) > 0

    # 3. Forecasting
    forecast = forecast_costs(calc_result)
    assert forecast is not None
    assert forecast["method"] in ["linear_regression", "moving_average_7d"]
    assert "predicted_cost_next_7_days" in forecast
    assert "confidence_interval_30d" in forecast

    # 4. Optimization
    optimization = generate_optimizations(calc_result, analysis)
    assert "total_potential_savings_pct" in optimization
    assert "total_potential_savings_usd" in optimization
    assert len(optimization["recommendations"]) > 0
    
    # Check that recommendations have priorities and dollar savings
    rec = optimization["recommendations"][0]
    assert "priority_score" in rec
    assert "estimated_savings_usd" in rec

