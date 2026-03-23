"""
CloudSage Cost Calculation Engine
=================================
Parses CSV uploads (AWS, Azure, custom formats), auto-detects columns via
alias mapping, validates/cleans data, and computes accurate per-row and
total costs using Python's Decimal module.
"""

import pandas as pd
import io
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column alias lists — each list maps common CSV header names to a canonical
# role. Normalisation strips spaces, underscores, and lowercases everything
# so "Usage Quantity" matches "usagequantity".
# ---------------------------------------------------------------------------
USAGE_ALIASES = [
    'usage', 'usagequantity', 'quantity', 'usageamount',
    'usageamountinunits', 'lineitemusageamount', 'consumedquantity',
]
UNIT_COST_ALIASES = [
    'unitcost', 'costperunit', 'rate', 'price', 'unblendedrate',
    'blendedrate', 'effectivecost', 'unitprice', 'pretaxcost',
]
COST_ALIASES = [
    'cost', 'totalcost', 'lineitemunblendedcost', 'lineitemblendedcost',
    'costinbillingcurrency', 'costinpricingcurrency', 'amount'
]
SERVICE_ALIASES = [
    'service', 'product', 'servicename', 'productname',
    'lineitemproductcode', 'metercategory', 'resourcetype',
]
DATE_ALIASES = [
    'date', 'usagedate', 'usagestartdate', 'startdate', 'billingperiod',
    'billingperiodstartdate', 'timestamp', 'lineitemusagestartdate',
    'usageenddate', 'enddate',
]
REGION_ALIASES = [
    'region', 'location', 'resourcegroup', 'availabilityzone',
    'meterregion', 'resourcegroup', 'productregion'
]

def normalize_col(col_name: str) -> str:
    """Normalizes a column name by lowercasing and removing spaces/underscores."""
    return str(col_name).lower().replace(' ', '').replace('_', '').replace('-', '').strip()


def _detect_column(norm_to_orig: dict, aliases: list) -> str | None:
    """Return the *original* column name for the first alias that matches."""
    return next((norm_to_orig[a] for a in aliases if a in norm_to_orig), None)


def process_csv_content(file_content: bytes) -> dict:
    """
    Processes raw CSV bytes and returns cost calculation results.

    Steps:
      1. Parse CSV (all columns kept as str for safe type conversion).
      2. Auto-detect usage, unit_cost, service, and date columns via aliases.
      3. Validate & coerce numeric fields; drop malformed rows.
      4. Compute per-row cost using Decimal for accuracy.
      5. Return results including a private '_dataframe' for downstream modules.

    Returns:
        dict with keys: detected_columns, total_cost, breakdown, _dataframe
    """
    if not file_content.strip():
        raise ValueError("Received empty file content")

    # ---- Parse CSV --------------------------------------------------------
    try:
        df = pd.read_csv(io.BytesIO(file_content), dtype=str)
    except pd.errors.EmptyDataError:
        raise ValueError("CSV is empty or contains no parseable data")
    except Exception as e:
        logger.error(f"Failed to parse CSV: {e}")
        raise ValueError("Invalid CSV format or corrupted file")

    initial_row_count = len(df)
    if initial_row_count == 0:
        raise ValueError("CSV contains headers but no data rows.")

    # ---- Auto-detect columns via alias mapping ----------------------------
    norm_mapping = {col: normalize_col(col) for col in df.columns}
    norm_to_orig = {v: k for k, v in norm_mapping.items()}

    usage_col = _detect_column(norm_to_orig, USAGE_ALIASES)
    unit_cost_col = _detect_column(norm_to_orig, UNIT_COST_ALIASES)
    cost_col = _detect_column(norm_to_orig, COST_ALIASES)
    service_col = _detect_column(norm_to_orig, SERVICE_ALIASES)
    date_col = _detect_column(norm_to_orig, DATE_ALIASES)
    region_col = _detect_column(norm_to_orig, REGION_ALIASES)

    # Allow processing if we have either (usage AND unit_cost) OR just 'cost'
    can_compute_cost = (usage_col and unit_cost_col) or cost_col

    if not can_compute_cost:
        detected = list(df.columns[:5])
        logger.warning(
            f"Could not calculate cost. Found columns: {detected}..."
        )
        raise ValueError(
            "Could not detect cost columns automatically. Your CSV must contain either "
            "a 'Cost' / 'TotalCost' column, OR both 'Usage' and 'UnitCost' / 'Rate' columns."
        )

    logger.info(
        f"Detected columns — cost: '{cost_col}', usage: '{usage_col}', unit_cost: "
        f"'{unit_cost_col}', service: '{service_col}', date: '{date_col}'"
    )

    # ---- Validate numeric convertibility ----------------------------------
    if cost_col:
        df['__pre_cost_num'] = pd.to_numeric(df[cost_col], errors='coerce')
    if usage_col:
        df['__usage_num'] = pd.to_numeric(df[usage_col], errors='coerce')
    if unit_cost_col:
        df['__unit_cost_num'] = pd.to_numeric(df[unit_cost_col], errors='coerce')

    # Drop rows depending on the calculation path
    if cost_col:
        valid_df = df.dropna(subset=['__pre_cost_num']).copy()
    else:
        valid_df = df.dropna(subset=['__usage_num', '__unit_cost_num']).copy()

    skipped_rows = initial_row_count - len(valid_df)

    if valid_df.empty:
        raise ValueError(f"Found required columns, but no valid numeric data remained after dropping {skipped_rows} invalid rows.")

    # ---- Compute costs with Decimal precision -----------------------------
    breakdown = []
    total_cost_decimal = Decimal('0.0')

    # Helper function to extract a clean string
    def get_clean_string(row, col):
        if not col or pd.isna(row.get(col)): return "Unknown"
        val = str(row.get(col, '')).strip()
        return val if val and val.lower() != 'nan' else "Unknown"

    for _, row in valid_df.iterrows():
        try:
            # 1. Prioritize pre-computed cost if available
            if cost_col:
                cost_val = Decimal(str(row[cost_col]).strip())
                usage_val = Decimal(str(row[usage_col]).strip()) if usage_col and not pd.isna(row.get(usage_col)) else Decimal('1.0')
                unit_cost_val = cost_val / usage_val if usage_val != 0 else cost_val
            # 2. Fall back to usage * unit_cost
            else:
                usage_val = Decimal(str(row[usage_col]).strip())
                unit_cost_val = Decimal(str(row[unit_cost_col]).strip())
                cost_val = usage_val * unit_cost_val

            total_cost_decimal += cost_val

            svc = get_clean_string(row, service_col)
            region = get_clean_string(row, region_col)

            item = {
                "service": svc,
                "usage": float(usage_val),
                "unit_cost": float(unit_cost_val),
                "cost": float(round(cost_val, 4)),
            }
            if region != "Unknown":
                item["region"] = region
            breakdown.append(item)

        except InvalidOperation as e:
            logger.warning(f"Could not calculate decimal value for row: {e}")
            continue
        except Exception as e:
            logger.warning(f"Unexpected error processing row: {e}")
            continue

    if not breakdown:
        raise ValueError(
            "No computation could be performed due to invalid data in remaining rows"
        )

    # ---- Build detected_columns map ---------------------------------------
    detected_cols = {}
    if cost_col: detected_cols["cost"] = cost_col
    if usage_col: detected_cols["usage"] = usage_col
    if unit_cost_col: detected_cols["unit_cost"] = unit_cost_col
    if service_col: detected_cols["service"] = service_col
    if date_col: detected_cols["date"] = date_col
    if region_col: detected_cols["region"] = region_col

    # ---- Add computed cost column to the DataFrame for downstream use -----
    valid_df = valid_df.copy()
    
    def calculate_row_cost(r):
        if cost_col: return float(Decimal(str(r[cost_col]).strip()))
        return float(Decimal(str(r[usage_col]).strip()) * Decimal(str(r[unit_cost_col]).strip()))

    valid_df['__computed_cost'] = valid_df.apply(calculate_row_cost, axis=1)
    
    # Ensure there's a fallback for `__usage_num` if it's missing but we had cost
    if '__usage_num' not in valid_df.columns:
        valid_df['__usage_num'] = 1.0

    valid_df['__service'] = valid_df.apply(lambda r: get_clean_string(r, service_col), axis=1)
    if region_col:
        valid_df['__region'] = valid_df.apply(lambda r: get_clean_string(r, region_col), axis=1)

    return {
        "detected_columns": detected_cols,
        "total_cost": float(round(total_cost_decimal, 2)),
        "breakdown": breakdown,
        "stats": {
            "total_rows": initial_row_count,
            "valid_rows": len(valid_df),
            "skipped_rows": skipped_rows
        },
        # Private: used by analyzer / forecaster — never serialized to API
        "_dataframe": valid_df,
        "_date_col": date_col,
        "_service_col": service_col,
        "_region_col": region_col,
    }
