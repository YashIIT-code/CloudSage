"""
Tests for CloudSage cost_service module.
Verifies CSV parsing, column detection, cost calculation, and edge cases.
"""
import pytest
from services.cost_service import process_csv_content


def test_valid_csv_standard():
    csv_data = b"service,usage,unit_cost\napi_calls,1000,0.002\nstorage,50,0.10"
    result = process_csv_content(csv_data)

    # 1000 * 0.002 = 2.0, 50 * 0.10 = 5.0, Total = 7.00
    assert result["total_cost"] == 7.00
    assert len(result["breakdown"]) == 2
    assert result["breakdown"][0]["cost"] == 2.0000
    assert result["breakdown"][1]["cost"] == 5.0000
    # Verify private DataFrame is returned for downstream modules
    assert "_dataframe" in result


def test_missing_service_column():
    csv_data = b"usage,unit_cost\n1000,0.002\n50,0.10"
    result = process_csv_content(csv_data)

    assert result["total_cost"] == 7.00
    assert result["breakdown"][0]["service"] == "Unknown"
    assert result["breakdown"][1]["service"] == "Unknown"


def test_missing_required_columns():
    # Only usage provided, missing unit_cost
    csv_data = b"service,usage\napi_calls,1000"
    with pytest.raises(ValueError, match="Could not detect cost columns automatically.*"):
        process_csv_content(csv_data)


def test_handling_invalid_values():
    csv_data = b"service,usage,unit_cost\napi_calls,1000,0.002\ninvalid_row,ab,10\nstorage,50,0.10\nempty_row,,"
    result = process_csv_content(csv_data)

    # Drops 'invalid_row' and 'empty_row'
    assert result["total_cost"] == 7.00
    assert len(result["breakdown"]) == 2


def test_empty_file_handling():
    with pytest.raises(ValueError, match="Received empty file content"):
        process_csv_content(b"")

    with pytest.raises(ValueError, match="CSV contains headers but no data rows."):
        process_csv_content(b"service,usage,unit_cost\n")


def test_whitespace_and_case_format():
    csv_data = b" SERVICE , USAGe , Unit_Cost \nabc, 100 , 0.5\n"
    result = process_csv_content(csv_data)

    assert result["total_cost"] == 50.0
    assert result["breakdown"][0]["service"] == "abc"


def test_no_valid_rows():
    csv_data = b"service,usage,unit_cost\nfoo,bar,baz\ntest,, "
    with pytest.raises(ValueError, match="Found required columns, but no valid numeric data remained.*"):
        process_csv_content(csv_data)


def test_extreme_precision():
    csv_data = b"service,usage,unit_cost\nprecise_math,100.001,0.0033\n"
    result = process_csv_content(csv_data)

    assert result["breakdown"][0]["cost"] == 0.3300  # rounded to 4 decimals
    assert result["total_cost"] == 0.33


def test_aws_alias_columns():
    """Test AWS Cost and Usage Report column aliases."""
    csv_data = b"ProductName,UsageQuantity,UnblendedRate,Tags\nAmazonEC2,50,0.22,web\nAmazonS3,100,0.01,storage"
    result = process_csv_content(csv_data)

    assert result["total_cost"] == 12.0
    assert result["detected_columns"]["usage"] == "UsageQuantity"
    assert result["detected_columns"]["unit_cost"] == "UnblendedRate"
    assert result["detected_columns"]["service"] == "ProductName"


def test_date_column_detection():
    """Test that date columns are detected via aliases."""
    csv_data = (
        b"service,usage,unit_cost,UsageStartDate\n"
        b"EC2,100,0.22,2024-01-01\n"
        b"S3,50,0.01,2024-01-02\n"
    )
    result = process_csv_content(csv_data)
    assert "date" in result["detected_columns"]
    assert result["detected_columns"]["date"] == "UsageStartDate"
