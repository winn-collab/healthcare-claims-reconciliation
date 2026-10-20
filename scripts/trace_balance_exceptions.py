"""Export exact-decimal evidence for every positive recorded claim balance.

This diagnoses source inconsistencies; it does not overwrite balances or
assume that transaction reconciliation proves the complete encounter was paid.
"""
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/synthea_sample_data_csv_latest"
ZERO = Decimal("0.00")


def money(value):
    return None if pd.isna(value) else Decimal(value)


def main():
    claims = pd.read_csv(SOURCE / "claims.csv", dtype=str)
    encounters = pd.read_csv(SOURCE / "encounters.csv", dtype=str)
    transactions = pd.read_csv(SOURCE / "claims_transactions.csv", dtype=str)
    balance_fields = ["OUTSTANDING1", "OUTSTANDING2", "OUTSTANDINGP"]
    balances = claims[balance_fields].apply(lambda col: col.map(money))
    positive = balances.apply(
        lambda col: col.map(lambda value: value is not None and value > ZERO)
    ).any(axis=1)
    selected = claims.loc[positive].merge(
        encounters, left_on="APPOINTMENTID", right_on="Id",
        how="left", validate="many_to_one", suffixes=("_claim", "_encounter"),
        indicator=True,
    )
    if not selected["_merge"].eq("both").all():
        raise ValueError("An exception has no matching encounter.")
    rows = []
    for _, claim in selected.iterrows():
        detail = transactions.loc[transactions.CLAIMID.eq(claim.Id_claim)]
        totals = {}
        for category, column in [("CHARGE", "AMOUNT"), ("PAYMENT", "PAYMENTS")]:
            values = detail.loc[detail.TYPE.eq(category), column]
            if values.empty or values.isna().any():
                raise ValueError(f"{claim.Id_claim}: incomplete {category} evidence")
            totals[category] = sum((Decimal(v) for v in values), ZERO)
        # Eight death-certification cases show $211.38 in encounter costs but
        # only $136.80 on each exported transaction side: $74.58 each is absent.
        # Reviewed Synthea code includes reports in claim costs but omits them
        # from item transactions. Balanced exports therefore do not establish
        # full payment. See reconcile_claim_balances.py for sources and the
        # qualification that this archive's generator version is unverified.
        base = Decimal(claim.BASE_ENCOUNTER_COST)
        total = Decimal(claim.TOTAL_CLAIM_COST)
        covered = Decimal(claim.PAYER_COVERAGE)
        primary = money(claim.OUTSTANDING1)
        secondary = money(claim.OUTSTANDING2)
        patient = money(claim.OUTSTANDINGP)
        rows.append({
            "claim_id": claim.Id_claim,
            "encounter_id": claim.APPOINTMENTID,
            "description": claim.DESCRIPTION,
            "base_encounter_cost": base,
            "total_encounter_claim_cost": total,
            "transaction_charges": totals["CHARGE"],
            "transaction_payments": totals["PAYMENT"],
            "transaction_difference": totals["CHARGE"] - totals["PAYMENT"],
            "encounter_cost_not_in_charge_export": total - totals["CHARGE"],
            "cost_above_base": total - base,
            "payer_coverage": covered,
            "recorded_primary_balance": primary,
            "recorded_secondary_balance": secondary,
            "recorded_patient_balance": patient,
            "primary_equals_payer_coverage": primary == covered,
            "patient_equals_total_minus_coverage": patient == total - covered,
            "secondary_repeats_primary_without_secondary_insurance": (
                pd.isna(claim.SECONDARYPATIENTINSURANCEID)
                and secondary is not None and secondary == primary and secondary > ZERO
            ),
        })
    result = pd.DataFrame(rows)
    output = ROOT / "outputs/balance_exception_trace.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))
    print(f"\nSaved {len(result)} exception traces to {output}")
    print("Unrepresented encounter costs:", sum(
        result.encounter_cost_not_in_charge_export, ZERO
    ))


if __name__ == "__main__":
    main()
