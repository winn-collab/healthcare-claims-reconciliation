"""Independently verify this dataset's portfolio claims using decimal arithmetic.

Read-only for source/analysis files; writes outputs/verification_summary.json.
Checks are specific to this archived sample, not universal financial rules.
No database connection or language model is required.
"""
import csv
import hashlib
import json
import platform
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/synthea_sample_data_csv_latest"
ZERO = Decimal("0")
CENT = Decimal("0.01")
TOLERANCE = Decimal("0.005")


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def amount(value):
    if not value or not value.strip():
        raise ValueError("Required amount is blank")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Required amount is not finite")
    return result


def indexed(rows, key):
    ids = [row[key] for row in rows]
    if any(not value.strip() for value in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"Missing/duplicate {key} identifiers")
    return {row[key]: row for row in rows}


def main():
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "status": "pass" if passed else "fail",
                       "detail": detail})

    inventory = []
    for path in sorted(RAW.glob("*.csv")):
        rows = read(path)
        inventory.append({"file": path.name, "rows": len(rows),
                          "columns": len(rows[0]) if rows else 0,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    archive = ROOT / "data/raw/synthea_sample_data_csv_latest.zip"
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    with ZipFile(archive) as bundle:
        matches = all(
            hashlib.sha256(bundle.read(item["file"])).hexdigest() == item["sha256"]
            for item in inventory
        )
    check("Extracted CSVs match archived bytes", matches, f"{len(inventory)} files")

    claims = indexed(read(RAW / "claims.csv"), "Id")
    encounters = indexed(read(RAW / "encounters.csv"), "Id")
    transactions = read(RAW / "claims_transactions.csv")
    indexed(transactions, "ID")
    check("Unique populated claim/encounter/transaction IDs", True,
          f"{len(claims)} claims; {len(encounters)} encounters; {len(transactions)} transactions")
    check("Sample population counts", (len(claims), len(encounters), len(transactions))
          == (9421, 5571, 85047), "Expected 9,421 / 5,571 / 85,047")
    orphaned = sum(t["CLAIMID"] not in claims for t in transactions)
    check("Transaction claim references", orphaned == 0, f"{orphaned} orphaned/missing")
    mismatched = sum(
        c["APPOINTMENTID"] not in encounters
        or encounters[c["APPOINTMENTID"]]["PATIENT"] != c["PATIENTID"]
        for c in claims.values()
    )
    check("Claim encounter/patient consistency", mismatched == 0, f"{mismatched} issues")
    referenced = {c["APPOINTMENTID"] for c in claims.values()}
    uncovered = len(set(encounters) - referenced)
    check("Encounter claim coverage", uncovered == 0, f"{uncovered} encounters without claims")

    totals = defaultdict(lambda: {"CHARGE": ZERO, "PAYMENT": ZERO})
    represented = defaultdict(set)
    for row in transactions:
        kind = row["TYPE"]
        if kind in ("CHARGE", "PAYMENT"):
            field = "AMOUNT" if kind == "CHARGE" else "PAYMENTS"
            totals[row["CLAIMID"]][kind] += amount(row[field])
            represented[row["CLAIMID"]].add(kind)
    missing = sum(represented[key] != {"CHARGE", "PAYMENT"} for key in claims)
    differences = sum(abs(totals[key]["CHARGE"] - totals[key]["PAYMENT"])
                      > TOLERANCE for key in claims)
    charges = sum((totals[key]["CHARGE"] for key in claims), ZERO)
    payments = sum((totals[key]["PAYMENT"] for key in claims), ZERO)
    check("Charge/payment coverage", missing == 0, f"{missing} incomplete claim summaries")
    check("Claim-level transaction reconciliation", differences == 0,
          f"{differences} differences above $0.005")
    check("Sample monetary reference", charges == payments == Decimal("15795506.28"),
          f"Charges {charges}; payments {payments}")

    positive = {key for key, c in claims.items() if any(
        c[field].strip() and amount(c[field]) > ZERO
        for field in ("OUTSTANDING1", "OUTSTANDING2", "OUTSTANDINGP")
    )}
    gaps = {key: amount(encounters[claims[key]["APPOINTMENTID"]]["TOTAL_CLAIM_COST"])
            - totals[key]["CHARGE"] for key in positive}
    check("Exception population/context", len(positive) == 8 and all(
        encounters[claims[key]["APPOINTMENTID"]]["DESCRIPTION"] == "Death Certification"
        for key in positive), f"{len(positive)} positive-balance claims")
    check("Investigated encounter-cost gaps", all(g == Decimal("74.58") for g in gaps.values())
          and sum(gaps.values(), ZERO) == Decimal("596.64"),
          f"Total investigated gap {sum(gaps.values(), ZERO)}")

    for relative, key in [("outputs/claim_reporting.csv", "claim_id"),
                          ("data/processed/claim_analysis.csv", "Id")]:
        exported = indexed(read(ROOT / relative), key)
        consistent = set(exported) == set(claims) and all(
            abs(amount(exported[claim][field]) - totals[claim][kind]) <= TOLERANCE
            for claim in claims if claim in exported
            for field, kind in [("charges", "CHARGE"), ("payments", "PAYMENT")]
        )
        check(f"Export identity and claim totals: {relative}", consistent,
              f"{len(exported)} unique exported claims; tolerance $0.005")
        if key == "claim_id":
            flags = {claim for claim, row in exported.items()
                     if row["positive_recorded_balance_flag"] == "1"}
            check("Reporting exception flags", flags == positive, f"{len(flags)} flagged claims")
    trace = indexed(read(ROOT / "outputs/balance_exception_trace.csv"), "claim_id")
    check("Saved exception trace", set(trace) == positive and all(
        amount(trace[key]["encounter_cost_not_in_charge_export"]) == gaps[key]
        and amount(trace[key]["transaction_charges"]) == totals[key]["CHARGE"]
        and amount(trace[key]["transaction_payments"]) == totals[key]["PAYMENT"]
        for key in positive if key in trace), f"{len(trace)} exception rows")

    categories = defaultdict(lambda: {"claims": 0, "encounters": set(), "charges": ZERO,
                                      "payments": ZERO})
    for key, claim in claims.items():
        encounter = encounters[claim["APPOINTMENTID"]]
        group = categories[encounter["ENCOUNTERCLASS"]]
        group["claims"] += 1
        group["encounters"].add(encounter["Id"])
        group["charges"] += totals[key]["CHARGE"]
        group["payments"] += totals[key]["PAYMENT"]
    for relative, field in [("data/processed/financial_summary_by_category.csv", "ENCOUNTERCLASS"),
                            ("outputs/category_totals_202610061431.csv", "encounter_category")]:
        saved = indexed(read(ROOT / relative), field)
        consistent = set(saved) == set(categories) and all(
            int(saved[k]["claim_count"]) == g["claims"]
            and int(saved[k]["encounter_count"]) == len(g["encounters"])
            and amount(saved[k]["charges"]).quantize(CENT) == g["charges"].quantize(CENT)
            and amount(saved[k]["payments"]).quantize(CENT) == g["payments"].quantize(CENT)
            for k, g in categories.items() if k in saved
        )
        check(f"Category count/totals: {relative}", consistent, f"{len(saved)} categories")
    result = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "archive_sha256": archive_hash,
        "status": "pass" if all(c["status"] == "pass" for c in checks) else "fail",
        "scope": "Archived CSVs and saved exports; no live MySQL or Power BI inspection",
        "source_inventory": inventory, "checks": checks,
        "transaction_types": dict(Counter(t["TYPE"] for t in transactions)),
        "power_bi_interaction_evidence": {
            "status": "user-demonstrated screenshots, not executed by this script",
            "ambulatory": {"claims": 4083, "charges": "12277051.63", "payments": "12277051.63",
                           "positive_balance_claims": 0},
            "cleared": {"claims": 9421, "charges": "15795506.28", "payments": "15795506.28",
                        "positive_balance_claims": 8},
        },
    }
    output = ROOT / "outputs/verification_summary.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    for entry in checks:
        print(f"{entry['status'].upper()}: {entry['check']} — {entry['detail']}")
    print(f"Saved {output}")
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
