from pathlib import Path

import pandas as pd

# Locate the unchanged source data.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/synthea_sample_data_csv_latest"


def total_by_claim(transactions, transaction_type, amount_column):
    """Return a financial total for each claim in one transaction category."""

    # Select claim references and amounts for the requested category.
    selected = transactions.loc[
        transactions["TYPE"].eq(transaction_type),
        ["CLAIMID", amount_column],
    ].copy()

    # Require populated claim references and amounts before aggregation.
    if selected.empty or selected.isna().any().any():
        raise ValueError(f"{transaction_type}: missing or absent input values")

    # Convert the selected amounts without modifying the source DataFrame.
    selected[amount_column] = pd.to_numeric(
        selected[amount_column], errors="raise"
    )

    # Combine amounts belonging to the same claim.
    return selected.groupby("CLAIMID")[amount_column].sum()

def inspect_recorded_balances(file_path):
    #I am inspecting how often something occurs in which case its below
    """Display recorded balance values and their frequencies"""
    # Recorded outstanding balance by responsible party
    # These source fields still require reconciliation with transactions

    balance_columns = [
        "OUTSTANDING1", # Amount owed by primary insurance
        "OUTSTANDING2", # Amount owed by secondary insurance
        "OUTSTANDINGP", # Amount owed by the patient
    ]

    #Load oly the balance fields needed for this inspection
    claims = pd.read_csv(
        file_path,
        usecols=[
            "Id", "STATUS1", "STATUS2", "STATUSP",
            *balance_columns,
            ],
        dtype=str,
    )

    #Retain missing values so they remain visible in the output
    print("\nRECORDED CLAIM BALANCES - VALUE COUNTS")
    for column in balance_columns:
        print(f"\n{column}")
        print(claims[column].value_counts(dropna=False).to_string())
    #Convert balance fields to numbers while preserving missing values
    balances  = claims[balance_columns].apply(
        pd.to_numeric, errors="raise"
    )

    #Select claims with a positive balance in at least one category
    positive_balance = balances.gt(0).any(axis=1)

    #Display each affected claim once, with its statues and source balance.
    affected_claims = claims.loc[positive_balance]

    print("\nCLAIMS WITH POSITIVE RECORDED BALANCES")
    print("DIstinct claim IDs:", affected_claims["Id"].nunique())
    print(affected_claims.to_string(index=False))
    # Make the selected claims available for futher analysis
    return affected_claims

def main():
    """Calculate preliminary overall and claim-level financial totals."""
    affected_claims = inspect_recorded_balances(DATA_DIR / "claims.csv")
    # Load only the columns required for this calculation.
    transactions = pd.read_csv(
        DATA_DIR / "claims_transactions.csv",
        usecols=["CLAIMID", "TYPE", "AMOUNT", "PAYMENTS",
                 "CHARGEID", "FROMDATE", "TODATE",
                 "ADJUSTMENTS", "TRANSFERS", "OUTSTANDING"],
        dtype=str,
    )
    #Inspect a claim whose recorded balance is positive despite matching Transaction charges and payments, to investigate the discrepancy
    claim_id = "1be83f06-48ef-7bac-6dc6-7fb4b0e23e4a"
    claim_details = transactions.loc[transactions["CLAIMID"].eq(claim_id)]
    print("\nTRANSACTIONS FOR CLAIM:", claim_id)
    print(claim_details.to_string(index=False))

    # Calculate charges and payments from their respective transaction rows.
    for transaction_type, column in [
        ("CHARGE", "AMOUNT"),
        ("PAYMENT", "PAYMENTS"),
    ]:
        selected = transactions.loc[
            transactions["TYPE"].eq(transaction_type), column
        ]

        # Stop if the selection is empty or contains recognized missing values.
        if selected.empty or selected.isna().any():
            raise ValueError(
                f"{transaction_type}: missing or absent input values"
            )

        # Stop on conversion failures instead of silently excluding them.
        amounts = pd.to_numeric(selected, errors="raise")

        # Report transaction counts and preliminary financial totals.
        print(f"\n{transaction_type}")
        print("Records:", amounts.count())
        print(f"Total: {amounts.sum():,.2f}")

    # Calculate separate charge and payment summaries at claim level.
    charges_by_claim = total_by_claim(transactions, "CHARGE", "AMOUNT")
    payments_by_claim = total_by_claim(transactions, "PAYMENT", "PAYMENTS")

    #Align charge and payment totals by claim ID, retaining both sets of IDs.
    comparison = pd.concat(
        [
            charges_by_claim.rename("charges"),
            payments_by_claim.rename("payments"),
        ],
        axis=1,
        join="outer",
    )
    # Load every source claim as the foundation of the analysis table
    claims = pd.read_csv(DATA_DIR / "claims.csv", dtype=str)

    #Require a populated, unique identifier for each claim
    if claims["Id"].isna().any() or claims["Id"].str.strip().eq("").any():
        raise ValueError("Source claims contain missing or blank IDs.")
    if claims["Id"].duplicated().any():
        raise ValueError("Source claims contain duplicate IDs.")

    #Attach aggregated transaction totals hile retaining every source claim
    claim_analysis = claims.merge(
        comparison,
        how="left",
        left_on="Id",
        right_index=True,
        validate="one_to_one",
        indicator=True,
    )

    #Preserve missing totals and flag them for review
    claim_analysis["missing_charge_summary"] = (
        claim_analysis["charges"].isna()

    )
    claim_analysis["missing_payment_summary"] = (
        claim_analysis["payments"].isna()
    )

      # Report coverage of every source claim after joining transaction summaries.
    print("\nFULL SOURCE CLAIM COVERAGE")
    print("Source claims:", len(claims))
    print("Rows after joining:", len(claim_analysis))

    print(
        "Claims without any transaction summary:",
        claim_analysis["_merge"].eq("left_only").sum(),
    )
    print(
        "Claims missing a charge summary:",
        claim_analysis["missing_charge_summary"].sum(),
    )
    print(
        "Claims missing a payment summary:",
        claim_analysis["missing_payment_summary"].sum(),
    )
    #Load encounter context and give join fields distinct names
    encounters = pd.read_csv(
        DATA_DIR / "encounters.csv",
        usecols=[
            "Id", "PATIENT", "ENCOUNTERCLASS",
            "DESCRIPTION", "ORGANIZATION",
        ],
        dtype=str,
    ).rename(columns={"Id": "encounter_id",
                      "PATIENT": "encounter_patient_id",
                      "DESCRIPTION": "encounter_description",
                      })
                      #Attach encounter context while preserving one row per source claim.
    claim_analysis = claim_analysis.merge(
        encounters,
        how="left",
        left_on="APPOINTMENTID",
        right_on="encounter_id",
        validate="many_to_one",
        indicator="encounter_match",
                      )
    # Check encounter coverage and patient consistency before analysis.
    matched_encounter = claim_analysis["encounter_match"].eq("both")
    patient_mismatch = matched_encounter & (
        claim_analysis["PATIENTID"].ne(
            claim_analysis["encounter_patient_id"]
        )
    )

    print("\nFULL CLAIM-ENCOUNTER COVERAGE")
    print("Source claims:", len(claims))
    print("Rows after encounter join:", len(claim_analysis))
    print("Claims without a matched encounter:", (~matched_encounter).sum())
    print("Matched encounters with a different patient:", patient_mismatch.sum())

    # Stop downstream analysis when the relationship checks fail.
    if len(claim_analysis) != len(claims):
        raise ValueError("The encounter join changed the claim row count.")

    if (~matched_encounter).any() or patient_mismatch.any():
        raise ValueError("Claim-encounter relationships require review.")
    # Summarize claim volume and financial activity by encounter category
    category_summary = claim_analysis.groupby(
        "ENCOUNTERCLASS", dropna=False
    ).agg(
        claim_count=("Id", "size"),
        encounter_count=("encounter_id", "nunique"),
        charges=("charges", "sum"),
        payments=("payments", "sum"),
    )

    #Rank categories by their share of total transaction charges
    category_summary["charge_share_pct"] = (
        category_summary["charges"]
        / claim_analysis["charges"].sum() * 100
    )
    category_summary =category_summary.sort_values(
        "charges", ascending=False
    )
    #Compare financial activity across categories after accounting for visiting colume.
    category_summary["charge_per_encounter"] = (
        category_summary["charges"]
        / category_summary["encounter_count"]
    )
    # Measure how many claims are associated with each encounter on average
    category_summary["claims_per_encounter"] = (
        category_summary["claim_count"]
        / category_summary["encounter_count"]
    )
    # Measure how many claims are associated with each encounter on average
    category_summary["claims_per_encounter"] = (
        category_summary["claim_count"]
        / category_summary["encounter_count"]
    )
    print("\nFINANCIAL ACTIVITY BY ENCOUNTER CATEGORY")
    print(
        category_summary.to_string(
            float_format=lambda value: f"{value:,.2f}"
        )

    )
    #Identify claims without a corresponding charge or payment summary.
    missing_side = comparison[["charges", "payments"]].isna().any(axis=1)

    #Compare only claims that have both totals
    matched = comparison.loc[~missing_side].copy()
    matched["difference"] = matched["charges"] - matched["payments"]

    #Flag differences greater than hald a cent to ignore tiny float errors
    different = matched["difference"].abs().gt(0.005)
    # Attach transaction summaries to each affected claim
    exception_review = affected_claims.merge(
        comparison,
        how = "left",
        left_on="Id",
        right_index=True,
        validate="one_to_one",
        indicator=True,
    )

    #Confirm that the join retained every affected claim
    if len(exception_review) != len(affected_claims):
        raise ValueError("The join changed the number of affected claims.")

    #Require a matching summary with both financial totals.
    if not exception_review["_merge"].eq("both").all():
        raise ValueError("An affected claim has no transaction summary.")
    if exception_review[["charges", "payments"]].isna().any().any():
        raise ValueError("An affected claim is missing a charge or paymnet total.")

    #Compare transaction totals alongside the recorded claim balances.
    exception_review["difference"] = (
        exception_review["charges"] - exception_review["payments"]

    )
    print ("\nAFFECTED CLAIMS - BALANCES AND TRANSACTION TOTALS")
    print("Rows before join:", len(affected_claims))
    print("Rows after join:", len(exception_review))
    print(exception_review.drop(columns="_merge").to_string(index=False))
       # Preview the comparison structure without limiting the analysis.
    print("\nPREVIEW — FIRST 5 CLAIMS")
    print("Display sample only; the full reconciliation follows below.")
    print(comparison.head().to_string(float_format=lambda value: f"{value:,.2f}"))

    # Report reconciliation results across all represented claims.
    print("\nFULL CLAIM RECONCILIATION")
    print("Distinct claims represented:", len(comparison))
    print("Claims missing a charge or payment summary:", missing_side.sum())
    print("Claims compared:", len(matched))
    print("Claims with a difference greater than $0.005:", different.sum())

    # Describe the result without implying that missing summaries passed.
    if different.any():
        print("Result: Financial differences require investigation.")
    elif missing_side.any():
        print("Result: Compared totals agree; missing summaries require review.")
    else:
        print("Result: All represented claims have both totals and agree")
        print("within the $0.005 comparison tolerance.")

    # Save derived analysis tables while preserving the raw source files.
    output_dir = PROJECT_ROOT / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    #Preserve one row per claim for detailed analysis and dashboard filtering.
    claim_analysis.to_csv(output_dir / "claim_analysis.csv", index=False)

    #Retain encounter categories as a column in the exported summary.
    category_summary.reset_index().to_csv(
        output_dir / "financial_summary_by_category.csv",
        index=False,
    )
    print("\nAnalysis tables saved to:", output_dir)
# Start the workflow only when this script is executed directly.
if __name__ == "__main__":
    main()
