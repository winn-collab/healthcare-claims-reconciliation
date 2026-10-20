-- Verify imported charge and payment totals against the Python results.
SELECT
    TYPE AS transaction_type,
    COUNT(*) AS transaction_count,
    SUM(
        CASE
            WHEN TYPE = 'CHARGE' THEN AMOUNT
            WHEN TYPE = 'PAYMENT' THEN PAYMENTS
        END
    ) AS total_amount
FROM cyberguard_meddicc.claims_transactions
WHERE TYPE IN ('CHARGE', 'PAYMENT')
GROUP BY TYPE
ORDER BY TYPE;
-- Summarize transaction amounts once per claim before joining.
WITH transaction_totals AS (
    SELECT
        CLAIMID,
        SUM(CASE WHEN TYPE = 'CHARGE' THEN AMOUNT END) AS charges,
        SUM(CASE WHEN TYPE = 'PAYMENT' THEN PAYMENTS END) AS payments
    FROM cyberguard_meddicc.claims_transactions
    GROUP BY CLAIMID
)
-- Retain every source claim and report coverage and financial differences.
SELECT
    COUNT(*) AS source_claims,
    COUNT(t.CLAIMID) AS claims_with_transactions,
    SUM(t.charges IS NULL) AS missing_charge_totals,
    SUM(t.payments IS NULL) AS missing_payment_totals,
    SUM(
        CASE
            WHEN ABS(t.charges - t.payments) > 0.005 THEN 1
            ELSE 0
        END
    ) AS claims_with_differences
FROM cyberguard_meddicc.claims AS c
LEFT JOIN transaction_totals AS t
    ON c.Id = t.CLAIMID;

-- Count all source encounters and identify any without a linked claim.
SELECT
    COUNT(*) AS total_encounters,
    SUM(
        NOT EXISTS (
            SELECT 1
            FROM cyberguard_meddicc.claims AS c
            WHERE c.APPOINTMENTID = e.Id
        )
    ) AS encounters_without_claims
FROM cyberguard_meddicc.encounters AS e;
