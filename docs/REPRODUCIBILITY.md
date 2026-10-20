# Reproduce the analysis

## What is preserved

Original source files remain local in `data/raw`; Git ignores this directory.
Small derived tables, code, and validation evidence are included in the public
package. Original archive hash:

```text
d61417b551e5b0997c33851b339c157421751f0ea68c18ea686ceb1850907c35
```

Data source: [official Synthea sample downloads](https://synthetichealth.github.io/downloads.html)
and [sample repository](https://github.com/synthetichealth/synthea-sample-data).
The archive used is named `synthea_sample_data_csv_latest.zip`:

https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_csv_latest.zip

The URL is mutable. A different hash means a different sample; do not expect the
same reference counts/results or change expected results merely to make checks
pass. Full source replay requires the retained archive or an identical upstream
download. The source distribution's terms should be reviewed separately from any
license chosen for original project code. No project license has been selected.

## Restore the raw source

From the repository root, create `data/raw`. Download or copy the archive there.
Check the digest before extraction:

```bash
sha256sum data/raw/synthea_sample_data_csv_latest.zip
```

If it matches, extract the archive's 18 CSVs into:

```text
data/raw/synthea_sample_data_csv_latest/
```

For the original flat ZIP:

```bash
mkdir -p data/raw/synthea_sample_data_csv_latest
unzip -n data/raw/synthea_sample_data_csv_latest.zip -d data/raw/synthea_sample_data_csv_latest
```

`-n` avoids overwriting existing files. The verifier also checks extracted bytes
against the archive. Unknown generator version remains unknown even with a hash.

## Python environment

The current verified runtime is Python 3.14.4. Installed versions are recorded
in [environment_snapshot.txt](environment_snapshot.txt). This records the local
environment; it is not a claim of tested availability across platforms or fresh
installation. Direct dependencies are in `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For an exact-version installation attempt, use
`python -m pip install -r docs/environment_snapshot.txt`. If a package/version
is unavailable, document the replacement and rerun verification. Avoid changing
the existing working environment just to test installation.

## Run order and outputs

| Command | Role | Writes |
|---|---|---|
| `python scripts/profile_sources.py` | Profile nine core tables and transaction types | Console |
| `python scripts/validate_financial_data.py` | Identifier/reference/numeric checks | Console |
| `python scripts/analyze_financials.py` | Claim totals, context, categories, balances | Two processed CSVs |
| `python scripts/reconcile_claim_balances.py` | Death-certification procedures/observations and report-cost hypothesis | Console |
| `python scripts/trace_balance_exceptions.py` | Exact-decimal evidence for positive balance claims | `outputs/balance_exception_trace.csv` |
| `python scripts/verify_portfolio.py` | Independent archived-data/export checks | `outputs/verification_summary.json` |

The analysis and trace commands intentionally regenerate their derived CSVs.
Preserve old outputs when comparing runs. The verifier reads raw/source exports
without modifying them and uses Python's standard library only.

## Optional MySQL path

Use MySQL 8.0+ for the CTE and window-function queries. The loader connects to
localhost:3306, database `cyberguard_meddicc`, username `cyberguard_user`, and
prompts securely for its password. It does not create the database/user.

1. In an administrative MySQL session, create `cyberguard_meddicc` and a local
   `cyberguard_user` with the table creation/read/insert permissions required by
   the loader. Keep the password outside scripts and version control.
2. Run `sql/01_create_tables.sql` in your SQL client. It defines encounter/claim
   schemas; initial row counts can be zero before loading.
3. Run `python scripts/load_source_tables.py`. It loads nine configured tables,
   creating missing table schemas as necessary.
4. Run `sql/02_validate_financials.sql`; compare financial/coverage results with
   Python references.
5. Run `sql/03_analyze_financial_activity.sql`; export the result as CSV with
   headers. The existing dated category export is retained as historical evidence.
6. Run `sql/04_prepare_claim_reporting.sql`; export its result as UTF-8 CSV with
   headers to `outputs/claim_reporting.csv`.
7. Run `python scripts/verify_portfolio.py` to compare that export against raw data.

Do not append repeated imports to populated tables. The loader skips matching
row counts; it does not prove those existing rows contain identical values.
Dates are mostly stored as source text; the reporting query casts service date.
Database setup and SQL-client export are manual dependencies, not an automated
one-command database deployment.

## Power BI reconstruction

Import `outputs/claim_reporting.csv`, preserve IDs as text, set service_date to
Date, and set charges/payments/balances to appropriate numeric types. Create the
four measures in [measures.dax](../powerbi/measures.dax). Build the documented
cards, charts, category slicer, and exception table. For the table, set its
visual-level positive_recorded_balance_flag filter to 1.

The measure file transcribes formulas recorded in the conversation; a live model
export is pending. Import/applied steps and the final chart's exact field mapping
are not fully exported. The current model has a single table, not star-schema
relationships. See [Power BI evidence](../powerbi/README.md) for accepted filter values.

## Verification boundaries

The 17 checks independently verify archived bytes, IDs, selected relationships,
selected financial inputs/totals, positive-balance cases, and saved category and
claim exports. They do not certify every source field, generator internals,
real-world accuracy, database contents, Power BI security, or future datasets.
Power BI interaction evidence is user-demonstrated, not a script-executed test.

All-claims charge/payment equality is a reference property of this sample.
Real datasets may have valid outstanding amounts, refunds, adjustments, and
payment delays. Do not reuse that equality as a universal acceptance rule.
