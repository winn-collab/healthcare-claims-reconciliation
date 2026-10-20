-- Combine transaction amounts into one row per claim.
WITH transaction_totals AS (
    SELECT
        CLAIMID,
        SUM(CASE WHEN TYPE = 'CHARGE' THEN AMOUNT END) AS charges,
        SUM(CASE WHEN TYPE = 'PAYMENT' THEN PAYMENTS END) AS payments
    FROM cyberguard_meddicc.claims_transactions
    GROUP BY CLAIMID
),
-- Group claim totals by category, counting each encounter once.
category_totals AS (
    SELECT
        e.ENCOUNTERCLASS AS encounter_category,
        COUNT(*) AS claim_count,
        COUNT(DISTINCT e.Id) AS encounter_count,
        SUM(t.charges) AS charges,
        SUM(t.payments) AS payments
    FROM cyberguard_meddicc.claims AS c
    LEFT JOIN transaction_totals AS t
        ON c.Id = t.CLAIMID
    LEFT JOIN cyberguard_meddicc.encounters AS e
        ON c.APPOINTMENTID = e.Id
    GROUP BY e.ENCOUNTERCLASS
)
-- Calculate each category's financial share, average, and rank.
SELECT
    encounter_category,
    claim_count,
    encounter_count,
    charges,
    payments,
    ROUND(
        100.0 * charges / NULLIF(SUM(charges) OVER (), 0),
        2
    ) AS charge_share_pct,
    ROUND(
        charges / NULLIF(encounter_count, 0),
        2
    ) AS charge_per_encounter,
    DENSE_RANK() OVER (ORDER BY charges DESC) AS charge_rank
FROM category_totals
ORDER BY charge_rank, encounter_category;