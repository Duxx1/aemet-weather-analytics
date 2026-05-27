import json
import re
import argparse
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Configuration

RAW_DIR = Path("data/raw/climatology/monthly")

# Fields that should be numeric and are stored as plain strings (no embedded metadata)
NUMERIC_FIELDS = {
    "hr", "w_rec", "w_med", "e",
    "tm_mes", "tm_max", "tm_min", "ti_max",
    "ts_min", "p_mes",
    "nw_55", "nw_91", "nt_30", "nt_00",
    "np_001", "np_010", "np_100", "np_300",
    "n_cub", "n_des", "n_nub", "n_llu", "n_tor", "n_nie",
    "inso", "p_sol",
    "q_med", "q_mar",
    "nv_0050", "nv_0100", "nv_1000",
}

# Fields that embed metadata in parentheses alongside the numeric value.
# Examples: "30.8(21)", "21/24.2(22)", "0.0(--)", "53.2(29/oct)"
FIELDS_WITH_METADATA = {
    "ta_max", "ta_min", "p_max", "q_max", "q_min",
    "w_racha", "ts_min", "ti_max",
}

# Regex patterns for date classification
PATTERN_MONTHLY_DATE = re.compile(r"^\d{4}-(0?[1-9]|1[0-2])$")
PATTERN_ANNUAL_DATE = re.compile(r"^\d{4}-13$")

# Explicit null value used by AEMET when a measurement is zero with no valid day: "0.0(--)"
PATTERN_NULL_VALUE = re.compile(r"^0\.0\(--\)$")

# Auxiliary functions

def classify_date(date: str) -> str:
    """
    Classifies a raw date string into one of three categories:
        - 'mensual': a valid month record (month 1-12, with or without leading zero)
        - 'anual': an annual summary record (month 13)
        - 'invalida': anything else
    """

    if PATTERN_ANNUAL_DATE.match(date):
        return "anual"
    if PATTERN_MONTHLY_DATE.match(date):
        return "mensual"
    
    return "invalida"


def extract_numeric(value: str, field_name: str = "") -> float | None:
    """
    Extracts the base numeric value from AEMET strings that embed metadata.
    Handles the following formats:
        - "30.8(21)"       -> 30.8   (value with day of occurrence)
        - "21/24.2(22)"    -> 24.2   (w_racha: direction/speed(day), we keep speed)
        - "0.0(--)"        -> 0.0    (explicit zero with no valid day)
        - "53.2(29/oct)"   -> 53.2   (annual summary with month label)

    Returns None if no numeric value can be extracted.
    """

    if not isinstance(value, str):
        return None

    # Explicit null value: treated as 0.0
    if PATTERN_NULL_VALUE.match(value.strip()):
        return 0.0

    # Only w_racha uses "direction/speed(day)" format
    if field_name == "w_racha" and "/" in value:
        parts = value.split("/", 1)
        if len(parts) == 2:
            value = parts[1]

    # Strip everything inside parentheses and any surrounding whitespace
    clean = re.sub(r"\([^)]*\)", "", value).strip()

    try:
        return float(clean)
    except ValueError:
        return None


# Validation logic

def validate_record(record: dict) -> dict:
    """
    Validates a single climatology record and returns a summary dict
    describing any issues found.

    Checks performed:
        1. Date format classification (mensual / anual / invalida)
        2. Empty records (only indicativo and fecha present)
        3. Sparse records (fewer than 5 data fields for a monthly record)
        4. Non-numeric values in fields that should be plain numbers
        5. Unparseable values in fields that embed metadata
    """

    issues = []
    indicativo = record.get("indicativo", "UNKNOWN")
    raw_fecha = record.get("fecha", "")

    date_type = classify_date(raw_fecha)
    if date_type == "invalida":
        issues.append(f"invalid_date:{raw_fecha}")

    # Count data fields, excluding the two identifier fields
    data_fields = set(record.keys()) - {"indicativo", "fecha"}

    if len(data_fields) == 0:
        issues.append("empty_record")

    # Monthly records with very few fields are flagged as sparse
    if date_type == "mensual" and 0 < len(data_fields) < 5:
        issues.append(f"sparse_record:{len(data_fields)}_fields")

    # Validate plain numeric fields
    for field in NUMERIC_FIELDS:
        if field in record:
            try:
                float(record[field])
            except (ValueError, TypeError):
                issues.append(f"non_numeric:{field}={record[field]}")

    # Validate fields that embed metadata in parentheses
    for field in FIELDS_WITH_METADATA:
            if field in record:
                val = record[field]
                if isinstance(val, str) and extract_numeric(val, field_name=field) is None:
                    issues.append(f"unexpected_format:{field}={val}")

    return {
        "indicativo": indicativo,
        "fecha": raw_fecha,
        "date_type": date_type,
        "n_fields": len(data_fields),
        "issues": "; ".join(issues) if issues else "",
        "has_issues": len(issues) > 0,
    }


def validate_file(path: Path) -> list[dict]:
    """
    Loads a JSON file and validates each record inside it.
    Returns a list of validation result dicts, one per record.
    If the file cannot be read or parsed, returns a single error record.
    """

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return [{
            "indicativo": "?", "fecha": "?", "date_type": "?",
            "n_fields": 0, "issues": f"read_error:{e}",
            "has_issues": True, "_file": path.name,
        }]

    if not isinstance(data, list):
        return [{
            "indicativo": "?", "fecha": "?", "date_type": "?",
            "n_fields": 0, "issues": "json_not_a_list",
            "has_issues": True, "_file": path.name,
        }]

    results = []
    for record in data:
        r = validate_record(record)
        r["_file"] = path.name
        results.append(r)
    
    return results


# Report
def print_report(df: pd.DataFrame) -> None:
    """Prints a structured validation summary to the terminal."""

    total = len(df)
    total_files = df["_file"].nunique()
    total_stations = df["indicativo"].nunique()

    monthly = df[df["date_type"] == "mensual"]
    annual = df[df["date_type"] == "anual"]
    invalid_dates = df[df["date_type"] == "invalida"]
    empty = df[df["issues"].str.contains("empty_record", na=False)]
    sparse = df[df["issues"].str.contains("sparse_record", na=False)]
    with_issues = df[df["has_issues"]]

    print("\n" + "=" * 60)
    print("VALIDATION REPORT - RAW CLIMATOLOGY")
    print("=" * 60)
    print(f"  Files processed       : {total_files}")
    print(f"  Unique stations       : {total_stations}")
    print(f"  Total records         : {total}")
    print(f"  Monthly records       : {len(monthly)}")
    print(f"  Annual records        : {len(annual)}")
    print(f"  Invalid dates         : {len(invalid_dates)}")
    print(f"  Empty records         : {len(empty)}")
    print(f"  Sparse records        : {len(sparse)}")
    print(f"  Records with issues   : {len(with_issues)} ({len(with_issues)/total*100:.1f}%)")

    # Field coverage for monthly records that are not empty
    monthly_with_data = monthly[~monthly["issues"].str.contains("empty_record", na=False)]
    if len(monthly_with_data):
        avg_fields = monthly_with_data["n_fields"].mean()
        print(f"\n  Avg fields per monthly record (non-empty): {avg_fields:.1f}")
        print(f"  Field count distribution (non-empty monthly records):")
        bins = [0, 5, 10, 15, 20, 30, 50]
        labels = ["1-5", "6-10", "11-15", "16-20", "21-30", "31+"]
        tmp = monthly_with_data.copy()
        tmp["field_range"] = pd.cut(tmp["n_fields"], bins=bins, labels=labels)
        dist = tmp["field_range"].value_counts().sort_index()
        for bucket, count in dist.items():
            print(f"    {bucket:>6} fields: {count:>5} records")

    # Issue type breakdown
    if len(with_issues):
        print("\n  Issue type breakdown:")
        issue_counts: dict[str, int] = defaultdict(int)
        for issue_str in with_issues["issues"]:
            for issue in issue_str.split("; "):
                key = issue.split(":")[0]
                issue_counts[key] += 1
        for key, n in sorted(issue_counts.items(), key=lambda x: -x[1]):
            print(f"    {key:<35}: {n}")

    # Sample of non-trivial problematic records
    notable = with_issues[
        ~with_issues["issues"].eq("empty_record") &
        ~with_issues["issues"].str.startswith("sparse_record")
    ]
    if len(notable):
        print(f"\n  Sample of non-trivial problematic records (max 10):")
        cols = ["_file", "indicativo", "fecha", "issues"]
        print(notable[cols].head(10).to_string(index=False))

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validates raw climatology JSON files downloaded from AEMET."
    )
    parser.add_argument(
        "--dir", default=str(RAW_DIR),
        help="Directory containing raw JSON files (default: data/raw/climatology/monthly)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Optional path to export the detailed validation report as CSV"
    )
    args = parser.parse_args()

    raw_dir = Path(args.dir)
    if not raw_dir.exists():
        print(f"ERROR: Directory '{raw_dir}' does not exist.")
        return

    files = sorted(raw_dir.glob("*.json"))
    if not files:
        print(f"No JSON files found in '{raw_dir}'.")
        return

    print(f"Processing {len(files)} files in '{raw_dir}'...")

    all_results = []
    for file in files:
        all_results.extend(validate_file(file))

    df = pd.DataFrame(all_results)

    print_report(df)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"Detailed report saved to: {output_path}")


if __name__ == "__main__":
    main()