# Power BI dashboard

I built this dashboard in Power BI Service using
[`outputs/claim_reporting.csv`](../outputs/claim_reporting.csv): one reporting
table with one row per claim. I prepared the data with Python and SQL before bringing it into Power BI.

## Visuals and measures

- Four cards: claim count, exported charges, exported payments, and claims with
  positive recorded balances.
- Category chart: Total Charges by Encounter Category.
- Year visual: Total Charges and Claim Count by Year.
- Encounter-category slicer and an exception table filtered to
  `positive_recorded_balance_flag = 1`.

[measures.dax](measures.dax) contains the four documented formulas. They have not
been compared with an exported live model. The year chart's exact field mapping
also needs confirmation in Power BI; the screenshot alone does not establish it.
The report title and Synthea source are visible in the overview; the cost-gap
explanation is in the [visual project report](../docs/PROJECT_BRIEF.pdf).

## How I checked the filter

| State | Claims | Charges | Payments | Flagged claims | Exception table |
|---|---:|---:|---:|---:|---|
| Ambulatory selected | 4,083 | $12,277,051.63 | $12,277,051.63 | 0 | Empty |
| Selection cleared | 9,421 | $15,795,506.28 | $15,795,506.28 | 8 | Restored |

I selected ambulatory encounters and checked the cards and exception table
against the expected results above. Then I cleared the selection and checked
that the full totals and all eight exceptions returned. The
[recording](screenshots/slicer-demo.mp4) shows these steps and other category
selections. I checked this manually; I did not automate testing of the live model.

## Dashboard files

- [Report overview](screenshots/overview.png).
- [Category-filter recording](screenshots/slicer-demo.mp4), approximately 39 seconds.
- [DAX definitions](measures.dax) and [reporting CSV](../outputs/claim_reporting.csv).

An editable PBIX/model and a separate dashboard PDF export are not included.
The three-page project report PDF is a separate narrative deliverable. The
exception table has horizontally scrollable columns; the CSV contains the full data.
See the [reproduction guide](../docs/REPRODUCIBILITY.md#power-bi-reconstruction)
for the steps to rebuild the dashboard and details of what still needs checking.
