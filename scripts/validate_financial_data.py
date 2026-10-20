from pathlib import Path

import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/synthea_sample_data_csv_latest"

#Validate claim identifiers and references from transaction records
def check_claim_relationships(claims,transactions):
    """Return issue counts for claim identifiers and transaction references."""
    # Select the claim reference recorded on each transaction
    claim_refs = transactions["CLAIMID"]
    #Identify populated references with no matching claim
    unmatched = claim_refs.notna() & ~claim_refs.isin(claims["Id"])
    #Return each validation label and its issue count
    return {
        "Missing claim IDs": claims["Id"].isna().sum(),
        "Duplicate claim IDs": claims["Id"].duplicated().sum(),
        "Missing transaction claim references": claim_refs.isna().sum(),
        "Transactions referencing absent claims": unmatched.sum(),
        }
def check_numeric_values(values):
    """Count missing values and values that cannot convert to numbers"""

    #Convert numeric text; unsuccessful conversions become missing vvalues.
    numbers = pd.to_numeric(values, errors="coerce")

    #Identify values that were present but failed numeric concersion
    invalid = values.notna() & numbers.isna()

    return{
        "Missing values": values.isna().sum(),
        "Invalid numeric values": invalid.sum(),

    }
def main():
    """Load source tables and report claim relationship issues."""

    #Preserve identifiers as text when reading the source files
    claims = pd.read_csv(DATA_DIR / "claims.csv", dtype=str)
    transactions = pd.read_csv(
        DATA_DIR / "claims_transactions.csv", dtype=str
    )
    #Inspect transaction identifiers before financial aggregation
    transaction_ids = transactions["ID"]

    print("\nTRANSACTION IDENTIFIER CHECKS")
    print("Missing transaction IDs:", transaction_ids.isna().sum())
    print(
        "Repeated transaction IDS after occurence:",
        transaction_ids.duplicated().sum(),
    )
    #Run the validation function and collect its named issue counts
    results = check_claim_relationships(claims, transactions)

    #Display each check and its corresponding issue count
    print("\nCLAIM RELATIONSHIP CHECKS")
    for check_name, issue_count in results.items():
        print(f"{check_name}: {issue_count}")
    #Validate the relevant financial field for each transaction category.
    for transaction_type, column in [
        ("CHARGE", "AMOUNT"),
        ("PAYMENT", "PAYMENTS"),
    ]:
        #Select this category's financial values.
        values = transactions.loc[
            transactions["TYPE"].eq(transaction_type), column
        ]

        #Report completeness and numeric conversion issues.
        checks = check_numeric_values(values)
        print(f"\n{transaction_type}:{column}")
        for check_name,issue_count in checks.items():
            print(f"{check_name}: {issue_count}")
#Start the workflow only when this script is excecuted directly
if __name__ == "__main__":
    main()
