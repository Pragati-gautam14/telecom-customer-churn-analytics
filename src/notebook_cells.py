CELLS = [
("md", """# Telecom Customer Churn Analytics — Walkthrough
**Business question:** Why are customers leaving, how much revenue does it cost, and which customers should the retention team call first?

**Data:** IBM Telco Customer Churn sample — 7,043 customers, 21 attributes (demographics, services, contract, billing, churn flag).
Pipeline: SQL (DuckDB) for cleaning and KPI tables → Python (SciPy, scikit-learn) for statistical tests and the predictive model."""),
("code", "import duckdb, pandas as pd, json\npd.set_option('display.width', 160)\ncon = duckdb.connect('../data/churn.duckdb', read_only=True)\nq = lambda s: con.sql(s).df()\nT = '../outputs/tables/'"),
("md", "## 1. Data quality"),
("code", "q('SELECT * FROM data_quality_log')"),
("md", "## 2. Headline KPIs: customer churn vs revenue churn"),
("code", "q('SELECT * FROM headline_kpis').T"),
("md", "Churners pay a higher monthly bill on average, so **revenue churn (≈30% of MRR) is higher than customer churn (26.5%)**."),
("md", "## 3. Churn by driver (SQL)"),
("code", "q(\"SELECT * FROM churn_by_dimension WHERE dimension IN ('Contract','Tenure band','Internet service','Payment method')\")"),
("md", "![drivers](../outputs/charts/01_churn_by_driver.png)\n![matrix](../outputs/charts/02_risk_matrix.png)"),
("code", "q('SELECT * FROM top_risk_segments')"),
("md", "## 4. Are the differences statistically significant?\nChi-square tests (categorical) with Cramér's V effect size; Mann-Whitney U for tenure and monthly charges (rank-biserial effect size)."),
("code", "pd.read_csv(T + 'driver_significance_tests.csv')"),
("md", "Tenure, contract, online security, tech support and internet type have the largest effects. Gender is **not** significant, so it is not a useful targeting criterion."),
("md", "## 5. Predictive model\nLogistic regression (interpretable) vs gradient boosting, stratified 75/25 split + 5-fold CV."),
("code", "display(pd.read_csv(T + 'model_performance.csv'))\njson.loads(open(T + 'model_summary.json').read())"),
("code", "pd.read_csv(T + 'logistic_odds_ratios.csv')"),
("md", "![odds](../outputs/charts/03_odds_ratios.png)"),
("md", "## 6. Turning the model into a retention plan"),
("code", "display(pd.read_csv(T + 'gains_by_decile.csv'))\ndisplay(pd.read_csv(T + 'active_customers_by_risk_tier.csv'))\npd.read_csv(T + 'retention_target_list_top500.csv').head(10)"),
("md", "![gains](../outputs/charts/04_gains_curve.png)"),
("md", """## 7. Recommendations
1. **Contract migration:** offer discounted 1-year upgrades to month-to-month customers in the first 6 months (55% churn in this cell).
2. **Fix the fiber experience:** fiber customers churn at 42% vs 19% on DSL despite paying more. Investigate pricing and service quality.
3. **Move e-check payers to autopay:** electronic-check customers churn at 45% vs 15–17% on automatic payments.
4. **Bundle tech support and online security:** each is linked to roughly a third of the churn rate.
5. **Use the risk score:** call the top 30% of customers first to reach ~67% of likely churners. The list is exported to `outputs/tables/retention_target_list_top500.csv`."""),
]
