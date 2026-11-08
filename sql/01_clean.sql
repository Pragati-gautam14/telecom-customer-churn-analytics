-- =============================================================
-- 01 · CLEAN & ENRICH CUSTOMER TABLE
-- 7,043 telecom customers, one row each. TotalCharges is blank for
-- 11 brand-new customers (tenure = 0) → set to 0.
-- =============================================================
CREATE OR REPLACE TABLE customers AS
SELECT
    customerID                                            AS customer_id,
    gender, SeniorCitizen = 1                             AS is_senior,
    Partner = 'Yes'                                       AS has_partner,
    Dependents = 'Yes'                                    AS has_dependents,
    tenure                                                AS tenure_months,
    CASE WHEN tenure <= 6  THEN '0-6 m'
         WHEN tenure <= 12 THEN '7-12 m'
         WHEN tenure <= 24 THEN '13-24 m'
         WHEN tenure <= 48 THEN '25-48 m'
         ELSE '49-72 m' END                               AS tenure_band,
    PhoneService, MultipleLines, InternetService,
    OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies,
    -- number of value-added services subscribed (0-6)
    (OnlineSecurity='Yes')::INT + (OnlineBackup='Yes')::INT + (DeviceProtection='Yes')::INT
      + (TechSupport='Yes')::INT + (StreamingTV='Yes')::INT + (StreamingMovies='Yes')::INT AS addon_count,
    Contract                                              AS contract,
    PaperlessBilling = 'Yes'                              AS paperless_billing,
    PaymentMethod                                         AS payment_method,
    MonthlyCharges                                        AS monthly_charges,
    COALESCE(TRY_CAST(NULLIF(TRIM(TotalCharges::VARCHAR), '') AS DOUBLE), 0) AS total_charges,
    (Churn = 'Yes')::INT                                  AS churned
FROM raw_churn;

CREATE OR REPLACE TABLE data_quality_log AS
SELECT 'Customers' AS check_name, COUNT(*) AS value FROM customers
UNION ALL SELECT 'Duplicate customer IDs', COUNT(*) - COUNT(DISTINCT customer_id) FROM customers
UNION ALL SELECT 'Blank TotalCharges (tenure 0) → 0', COUNT(*) FROM raw_churn WHERE TRIM(TotalCharges::VARCHAR) = ''
UNION ALL SELECT 'Negative charges', COUNT(*) FROM customers WHERE monthly_charges < 0 OR total_charges < 0;
