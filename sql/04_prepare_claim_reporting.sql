-- Aggregate transactions to one row per claim before joining.
WITH transaction_totals AS (
    SELECT
        CLAIMID,
        SUM(
            CASE WHEN TYPE = 'CHARGE' THEN AMOUNT END
        ) AS charges,
        SUM(
            CASE WHEN TYPE = 'PAYMENT' THEN PAYMENTS END
        ) AS payments
    FROM cyberguard_meddicc.claims_transactions
    GROUP BY CLAIMID
)

-- Retain every source claim and add its financial and encounter context.
SELECT
    c.Id AS claim_id,
    c.APPOINTMENTID AS encounter_id,
    CAST(LEFT(c.SERVICEDATE, 10) AS DATE) AS service_date,
    e.ENCOUNTERCLASS AS encounter_category,
    e.DESCRIPTION AS encounter_description,
    t.charges,
    t.payments,
    t.charges - t.payments AS transaction_difference,
    c.STATUS1 AS primary_insurance_status,
    c.STATUS2 AS secondary_insurance_status,
    c.STATUSP AS patient_status,
    c.OUTSTANDING1 AS recorded_primary_balance,
    c.OUTSTANDING2 AS recorded_secondary_balance,
    c.OUTSTANDINGP AS recorded_patient_balance,

    -- Flag positive source balances without treating them as confirmed debt.
    CASE
        WHEN c.OUTSTANDING1 > 0
          OR c.OUTSTANDING2 > 0
          OR c.OUTSTANDINGP > 0
        THEN 1
        ELSE 0
    END AS positive_recorded_balance_flag

FROM cyberguard_meddicc.claims AS c
LEFT JOIN transaction_totals AS t
    ON c.Id = t.CLAIMID
LEFT JOIN cyberguard_meddicc.encounters AS e
    ON c.APPOINTMENTID = e.Id;