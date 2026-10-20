from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/synthea_sample_data_csv_latest"


def main():
    """Inspect claim balances for all death-certification encounters."""
    encounters = pd.read_csv(DATA_DIR / "encounters.csv", dtype=str)
    claims = pd.read_csv(DATA_DIR / "claims.csv", dtype=str)

    # Select the complete encounter population for this service description.
    death_encounters = encounters.loc[
        encounters["DESCRIPTION"].eq("Death Certification"),
        ["Id", "BASE_ENCOUNTER_COST", "TOTAL_CLAIM_COST", "PAYER_COVERAGE"],
    ]

    # Retain every selected encounter and attach any associated claims.
    review = death_encounters.merge(
        claims[
            ["Id", "APPOINTMENTID", "STATUS1", "STATUS2", "STATUSP",
             "OUTSTANDING1", "OUTSTANDING2", "OUTSTANDINGP"]
        ],
        how="left",
        left_on="Id",
        right_on="APPOINTMENTID",
        suffixes=("_encounter", "_claim"),
        validate="one_to_many",
        indicator=True,
    )

    print("\nALL DEATH-CERTIFICATION ENCOUNTERS")
    print("Encounter records:", len(death_encounters))
    print("Distinct matched claims:", review["Id_claim"].nunique())
    print(
        "Encounters without a claim:",
        review.loc[
            review["_merge"].eq("left_only"), "Id_encounter"
        ].nunique(),
    )
    print(review.to_string(index=False))
    # Inspect procedures linked to every death-certification encounter.
    procedures = pd.read_csv(
        DATA_DIR / "procedures.csv",
        usecols=["ENCOUNTER", "CODE", "DESCRIPTION", "BASE_COST"],
        dtype=str,
    )

    selected_procedures = procedures.loc[
        procedures["ENCOUNTER"].isin(death_encounters["Id"])
    ].copy()

    print("\nPROCEDURES IN DEATH-CERTIFICATION ENCOUNTERS")
    print("Procedure records:", len(selected_procedures))
    print(selected_procedures.to_string(index=False))

    # Sum procedure costs by encounter without assuming absent records mean zero.
    selected_procedures["BASE_COST"] = pd.to_numeric(
        selected_procedures["BASE_COST"], errors="raise"
    )
    if selected_procedures["BASE_COST"].isna().any():
        raise ValueError("Selected procedures contain missing costs.")

    procedure_totals = selected_procedures.groupby("ENCOUNTER")[
        "BASE_COST"
    ].sum()

    cost_review = death_encounters.set_index("Id").copy()
    cost_review["BASE_ENCOUNTER_COST"] = pd.to_numeric(
        cost_review["BASE_ENCOUNTER_COST"], errors="raise"
    )
    cost_review["TOTAL_CLAIM_COST"] = pd.to_numeric(
        cost_review["TOTAL_CLAIM_COST"], errors="raise"
    )

    # Align procedure totals to encounter IDs and compare the cost components.
    cost_review["procedure_cost"] = procedure_totals
    cost_review["cost_above_base"] = (
        cost_review["TOTAL_CLAIM_COST"]
        - cost_review["BASE_ENCOUNTER_COST"]
    )
    cost_review["unexplained_difference"] = (
        cost_review["cost_above_base"] - cost_review["procedure_cost"]
    )

    print("\nENCOUNTER COST COMPONENT COMPARISON")
    print(cost_review.to_string())
    # Investigation finding (2026-10-12): all eight Death Certification
    # encounters total $211.38, but their exported charges and payments each
    # total only $136.80. The difference is $74.58 each ($596.64 overall).
    # Reviewed Synthea code creates a death-certificate Report, adds it to the
    # claim, and prices reports using laboratory costs. CSVExporter generates
    # item transactions for procedures, immunizations, and medications, but
    # excludes reports. This supports the report-cost explanation below.
    # Charges and payments still balance because neither exported side includes
    # the report; agreement does NOT prove the full encounter cost was paid.
    # In its BILLED branch, the exporter also uses cost allocations for the
    # OUTSTANDING fields, rather than subtracting exported payments, and may
    # repeat primary coverage in OUTSTANDING2 without secondary insurance.
    # Preserve these fields as source evidence, not confirmed unpaid debt.
    # Qualification: the archive's exact generator version/configuration is
    # unverified; this is a supported diagnosis, not a repaired generator bug.
    # Source files in https://github.com/synthetichealth/synthea/tree/master:
    # src/main/java/org/mitre/synthea/modules/DeathModule.java
    # src/main/java/org/mitre/synthea/world/concepts/HealthRecord.java
    # src/main/java/org/mitre/synthea/world/concepts/Costs.java
    # src/main/java/org/mitre/synthea/export/CSVExporter.java
    # Reproduce the transaction comparison with trace_balance_exceptions.py.
    default_report_cost = 100.00
    massachusetts_lab_factor = 0.7458
    expected_report_cost = round(
        default_report_cost * massachusetts_lab_factor, 2
    )

    # Compare the source-derived amount with each observed encounter difference.
    cost_review["matches_report_cost"] = (
        cost_review["cost_above_base"]
        .sub(expected_report_cost)
        .abs()
        .lt(0.005)
    )

    print("\nSOURCE-CODE EXPLANATION CHECK")
    print(f"Expected report cost: ${expected_report_cost:,.2f}")
    print("Encounters checked:", len(cost_review))
    print(
        "Encounters matching the expected report cost:",
        cost_review["matches_report_cost"].sum(),
    )
    #Inspect observations linked to the selected encounters for report context,
    observations = pd.read_csv(
    DATA_DIR / "observations.csv",
    usecols=["ENCOUNTER","CODE", "DESCRIPTION", "VALUE", "UNITS", "TYPE"],
    dtype=str,
    )
    selected_observations = observations.loc[
        observations["ENCOUNTER"].isin(death_encounters["Id"])

    ].copy()
    print("\nOBSERVATIONS IN DEATH-CERTIFICATION ENCOUNTERS")
    print("Observation records:", len(selected_observations))
    print(
        "Encounters represented:",
        selected_observations["ENCOUNTER"].nunique(),
    )
    print(selected_observations.to_string(index=False))
if __name__ == "__main__":
    main()
