# Power BI model & DAX measures

Load `customers_clean.csv` and `customer_risk_scores.csv` and relate them on `customer_id` (1:1).

```DAX
Customers          = COUNTROWS ( customers_clean )
Churned Customers  = CALCULATE ( [Customers], customers_clean[churned] = 1 )
Churn Rate %       = DIVIDE ( [Churned Customers], [Customers] )
MRR                = SUM ( customers_clean[monthly_charges] )
Churned MRR        = CALCULATE ( [MRR], customers_clean[churned] = 1 )
Revenue Churn %    = DIVIDE ( [Churned MRR], [MRR] )
Annualised Loss    = [Churned MRR] * 12
Churn vs Avg (pp)  = [Churn Rate %] - CALCULATE ( [Churn Rate %], ALL ( customers_clean ) )
High-Risk Active   = CALCULATE ( [Customers], customer_risk_scores[risk_tier] = "High", customers_clean[churned] = 0 )
High-Risk MRR      = CALCULATE ( [MRR], customer_risk_scores[risk_tier] = "High", customers_clean[churned] = 0 )
```

Suggested pages: **Overview** (KPI cards, churn by contract/tenure), **Drivers** (matrix visual contract × tenure_band with conditional formatting), **Retention list** (table of active customers filtered to the High risk tier, sorted by score).
