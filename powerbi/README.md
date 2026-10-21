# Power BI report and evidence

The report was authored in Power BI Service using `outputs/claim_reporting.csv`.
It has one semantic-model table with one row per claim. Upstream Python/SQL
performs relational preparation; this is not a Power BI star schema.

## Implemented report

- Title: Healthcare Revenue Cycle Analysis: Claims and Payment Reconciliation.
- Cards: Claim Count; Total Charges; Total Payments; Claims with Positive Recorded Balances.
- Category bar chart: Total Charges by Encounter Category.
- Year visual: Total Charges and Claim Count by Year (user-confirmed measure setup).
- Encounter-category slicer.
- Table filtered to positive recorded balances, containing eight claims unfiltered.
- Context note about synthetic data and $74.58 cost gaps.

The [DAX file](measures.dax) records four formulas from the learning history.
Measure definitions should be compared with the saved model when an editable
export becomes available. Formatting and interactions were reviewed from
screenshots, not by an API connection to the live model.

## Demonstrated interaction test

| State | Claim Count | Total Charges | Total Payments | Flagged claims | Exception table |
|---|---:|---:|---:|---:|---|
| Ambulatory selected | 4,083 | $12,277,051.63 | $12,277,051.63 | 0 | Empty |
| Category selection cleared | 9,421 | $15,795,506.28 | $15,795,506.28 | 8 | Restored |

## Preservation status

- Overview image: [report canvas](screenshots/overview.png), reviewed October 15, 2026.
- Filter recording: [category demonstration](screenshots/slicer-demo.mp4)
  (MP4, approximately 39 seconds), reviewed October 15, 2026. Shows the
  ambulatory state above, additional category selections, and restoration of
  the full totals and eight exception rows after clearing the selection.
- Optional editable `.pbix`/model export: pending, subject to service permissions
  and download mode. A live-connected PBIX is not a self-contained data snapshot.

The root README displays the overview and links to the recording. These files
are prepared locally; GitHub publication is still pending.

## Remaining presentation checks

The overview shows the full fourth-card label and all eight exception rows.
The exception table extends horizontally beyond the visible columns; the saved
CSV evidence provides the complete data. If an optional PDF is exported, review
its labels and context text separately because export may differ from the browser.

Power BI Service authoring, DAX measures, cards, charts, slicer, exception filter,
and demonstrated category filtering are supported resume claims. RLS, scheduled
refresh, drillthrough, custom page tooltips, full accessibility compliance,
performance optimization, and AI features are not established here.
