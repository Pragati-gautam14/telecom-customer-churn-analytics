-- =============================================================
-- 02 · CHURN KPIs & REVENUE AT RISK
-- Monthly recurring revenue (MRR) lost = sum of monthly charges of churners
-- =============================================================
CREATE OR REPLACE TABLE headline_kpis AS
SELECT
    COUNT(*)                                                            AS customers,
    SUM(churned)                                                        AS churned_customers,
    ROUND(100.0 * AVG(churned), 1)                                      AS churn_rate_pct,
    ROUND(SUM(monthly_charges), 0)                                      AS total_mrr,
    ROUND(SUM(monthly_charges) FILTER (WHERE churned = 1), 0)           AS churned_mrr,
    ROUND(100.0 * SUM(monthly_charges) FILTER (WHERE churned = 1) / SUM(monthly_charges), 1) AS mrr_churn_pct,
    ROUND(12 * SUM(monthly_charges) FILTER (WHERE churned = 1), 0)      AS annualised_revenue_lost,
    ROUND(AVG(monthly_charges) FILTER (WHERE churned = 1), 2)           AS avg_bill_churners,
    ROUND(AVG(monthly_charges) FILTER (WHERE churned = 0), 2)           AS avg_bill_retained,
    ROUND(AVG(tenure_months) FILTER (WHERE churned = 1), 1)             AS avg_tenure_churners,
    ROUND(AVG(tenure_months) FILTER (WHERE churned = 0), 1)             AS avg_tenure_retained
FROM customers;

-- Generic churn-by-dimension table (long format → easy to chart / Power BI)
CREATE OR REPLACE TABLE churn_by_dimension AS
WITH dims AS (
    SELECT 'Contract' AS dimension, contract AS value, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Tenure band', tenure_band, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Internet service', InternetService, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Payment method', payment_method, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Tech support', TechSupport, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Online security', OnlineSecurity, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Add-on services', addon_count::VARCHAR, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Senior citizen', CASE WHEN is_senior THEN 'Yes' ELSE 'No' END, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Paperless billing', CASE WHEN paperless_billing THEN 'Yes' ELSE 'No' END, churned, monthly_charges FROM customers
    UNION ALL SELECT 'Has dependents', CASE WHEN has_dependents THEN 'Yes' ELSE 'No' END, churned, monthly_charges FROM customers
)
SELECT dimension, value,
       COUNT(*)                                                     AS customers,
       SUM(churned)                                                 AS churned,
       ROUND(100.0 * AVG(churned), 1)                               AS churn_rate_pct,
       ROUND(SUM(monthly_charges) FILTER (WHERE churned = 1), 0)    AS churned_mrr,
       ROUND(100.0 * SUM(churned) / SUM(SUM(churned)) OVER (PARTITION BY dimension), 1) AS share_of_churners_pct
FROM dims
GROUP BY dimension, value
ORDER BY dimension, churn_rate_pct DESC;

-- Contract × tenure risk matrix
CREATE OR REPLACE TABLE risk_matrix AS
SELECT contract, tenure_band, COUNT(*) AS customers, ROUND(100.0 * AVG(churned), 1) AS churn_rate_pct
FROM customers GROUP BY ALL ORDER BY contract, tenure_band;

-- Highest-risk segment combinations (min 100 customers)
CREATE OR REPLACE TABLE top_risk_segments AS
SELECT contract, InternetService AS internet_service, payment_method,
       COUNT(*) AS customers, SUM(churned) AS churned,
       ROUND(100.0 * AVG(churned), 1) AS churn_rate_pct,
       ROUND(SUM(monthly_charges) FILTER (WHERE churned = 1), 0) AS churned_mrr
FROM customers GROUP BY ALL HAVING COUNT(*) >= 100
ORDER BY churn_rate_pct DESC LIMIT 10;
