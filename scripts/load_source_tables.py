from pathlib import Path

import pandas as pd

from getpass import getpass

from decimal import Decimal

from sqlalchemy import (
    URL, Column, MetaData, Numeric, String, Table,
    Text, create_engine, inspect, select, func, text,
)

# Locate source files relative to the project, regardless of terminal location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/synthea_sample_data_csv_latest"

# Define the source tables included in this loading workflow.
CORE_TABLES = [
    "patients",
    "organizations",
    "providers",
    "payers",
    "encounters",
    "conditions",
    "procedures",
    "claims",
    "claims_transactions",
]
# Store monetary source fields as exact decimals rather than floating-point values.
MONEY_COLUMNS = {
    "AMOUNT", "UNITAMOUNT", "PAYMENTS", "ADJUSTMENTS",
    "TRANSFERS", "OUTSTANDING",
    "OUTSTANDING1", "OUTSTANDING2", "OUTSTANDINGP",
    "BASE_ENCOUNTER_COST", "TOTAL_CLAIM_COST", "PAYER_COVERAGE",
    "BASE_COST", "HEALTHCARE_EXPENSES", "HEALTHCARE_COVERAGE",
    "INCOME", "REVENUE", "AMOUNT_COVERED", "AMOUNT_UNCOVERED",
}
def create_database_engine():
    """Configure access to the project's local MySQL database."""

    # Request the password without displaying or saving it in the script.
    password = getpass("MySQL password for cyberguard_user: ")

    # Build the connection address without manually joining credentials.
    database_url = URL.create(
        drivername="mysql+pymysql",
        username="cyberguard_user",
        password=password,
        host="localhost",
        port=3306,
        database="cyberguard_meddicc",
    )

    return create_engine(database_url)

def load_source_table(engine, table_name):
    """Load one source table without overwriting existing records."""
    file_path = DATA_DIR / f"{table_name}.csv"

    # Preserve source identifiers and recognized missing values.
    source = pd.read_csv(file_path, dtype=str)
    if source.empty:
        raise ValueError(f"{table_name}: the source file contains no rows.")

    metadata = MetaData()

    if inspect(engine).has_table(table_name):
        # Use the actual schema for tables already created in MySQL.
        target = Table(table_name, metadata, autoload_with=engine)
    else:
        # Use explicit financial types and preserve other source fields as text.
        columns = []
        for name in source.columns:
            if name in {"Id", "ID"}:
                column = Column(name, String(36), primary_key=True)
            elif name in MONEY_COLUMNS:
                column = Column(name, Numeric(15, 2))
            else:
                column = Column(name, Text)
            columns.append(column)

        target = Table(table_name, metadata, *columns)
        target.create(engine)

    # Reject schema differences before inserting any records.
    if set(source.columns) != set(target.columns.keys()):
        raise ValueError(f"{table_name}: CSV and database columns differ.")

    # Commit this table's inserts only if loading and the row-count check succeed.
    with engine.begin() as connection:
        existing_rows = connection.execute(
            select(func.count()).select_from(target)
        ).scalar_one()

        if existing_rows:
            if existing_rows != len(source):
                raise ValueError(
                    f"{table_name}: existing row count differs from the CSV."
                )
            print(f"SKIPPED {table_name}: {existing_rows:,} existing rows")
            return

        # Convert money directly from source text, preserving missing values.
        prepared = source.astype(object).where(source.notna(), None)
        for column in target.columns:
            if isinstance(column.type, Numeric):
                prepared[column.name] = prepared[column.name].map(
                    lambda value: Decimal(value) if value is not None else None
                )

        # Load in batches without writing the DataFrame index as a column.
        prepared.to_sql(
            table_name,
            con=connection,
            if_exists="append",
            index=False,
            chunksize=1000,
        )

        loaded_rows = connection.execute(
            select(func.count()).select_from(target)
        ).scalar_one()

        if loaded_rows != len(source):
            raise ValueError(f"{table_name}: imported row count does not match.")

        print(f"LOADED  {table_name}: {loaded_rows:,} rows")

def main():
    """Load the configured source tables and report each table's outcome."""
    engine = create_database_engine()

    try:
        for table_name in CORE_TABLES:
            load_source_table(engine, table_name)
        print("\nSource loading completed.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()