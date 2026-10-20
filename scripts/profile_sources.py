from pathlib import Path

import pandas as pd

#Locate the project from this script, regardless of terminal location
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/synthea_sample_data_csv_latest"

#Define the source tables included in the initial analysis scope
CORE_TABLES = ["patients", "encounters", "conditions", "claims", "procedures", "organizations", "payers", "claims_transactions", "providers"]

#TABLE Profiling
def profile_table(file_path):
    """Describe one source table/table structure without modifying it."""
    table = pd.read_csv(file_path, dtype=str)

    print(f"\nTABLE: {file_path.stem}")
    print("Rows and columns:", table.shape)
    print("Columns:", table.columns.tolist())

    # Count recognized missing values seperately for each column
    missing = table.isna().sum()
    # Restrict the displayed summary to columns containing missing values
    affected_columns = missing[missing > 0]

    print("Columns with missing values:")
    if affected_columns.empty:
        print("None")
    else:
        print(affected_columns.to_string())

    #Apply transaction-specific profiling only to the transactions table
    if file_path.stem == "claims_transactions":

        #Count records by transaction category, including missing categories
        # These are record counts, not financial totals
        print("\nTRANSACTION TYPES")
        print(table["TYPE"].value_counts(dropna=False))

        #Count missing AMOUNT values within each transaction category
        #Retain missing categories so their records are not excluded
        print("\nMISSING AMOUNT BY TRANSACTION TYPE")
        missing_amount = table["AMOUNT"].isna()
        print(
            missing_amount.groupby(
                table["TYPE"], dropna=False
            ).sum(
            )
        )

# WORKFLOW COORDINATION
def main():
    """Run source profiling for each table in the configured scope"""

    #Build each csv path and process one table at a time
    for table_name in CORE_TABLES:
        profile_table(DATA_DIR / f"{table_name}.csv")

# ENTRY POINT
# Run the workflow when this file is executed directly
# Importing this module elsewhere will not automatically run main()

if __name__ == "__main__":
    main()
