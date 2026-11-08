"""
Statistical tests + predictive churn model.
 - Chi-square test of independence for each categorical driver
 - Logistic regression (interpretable odds ratios) vs. Gradient Boosting
 - Decile / gains analysis to show how well the model targets retention offers
Run after run_pipeline.py:  python src/churn_model.py
"""
from pathlib import Path
import json
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tables"
SEED = 42

df = duckdb.connect(str(ROOT / "data" / "churn.duckdb"), read_only=True).table("customers").df()

CAT = ["contract", "InternetService", "payment_method", "OnlineSecurity", "TechSupport", "OnlineBackup",
       "DeviceProtection", "StreamingTV", "StreamingMovies", "MultipleLines", "PhoneService", "gender"]
BOOL = ["is_senior", "has_partner", "has_dependents", "paperless_billing"]
NUM = ["tenure_months", "monthly_charges", "total_charges", "addon_count"]

# ---------- 1. Statistical significance of drivers ----------
rows = []
for col in CAT + BOOL:
    ct = pd.crosstab(df[col], df.churned)
    chi2, p, dof, _ = chi2_contingency(ct)
    n = ct.values.sum()
    cramers_v = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
    rows.append(dict(feature=col, test="chi-square", statistic=round(chi2, 1), p_value=p, effect_size=round(cramers_v, 3)))
for col in ["tenure_months", "monthly_charges"]:
    a, b = df.loc[df.churned == 1, col], df.loc[df.churned == 0, col]
    u, p = mannwhitneyu(a, b)
    rows.append(dict(feature=col, test="Mann-Whitney U", statistic=round(u, 0), p_value=p,
                     effect_size=round(1 - 2 * u / (len(a) * len(b)), 3)))  # rank-biserial
stats = pd.DataFrame(rows).sort_values("effect_size", key=abs, ascending=False)
stats["significant_at_5pct"] = stats.p_value < 0.05
stats["p_value"] = stats.p_value.map(lambda v: f"{v:.2e}")
stats.to_csv(OUT / "driver_significance_tests.csv", index=False)

# ---------- 2. Models ----------
X = df[CAT + BOOL + NUM].copy()
X[BOOL] = X[BOOL].astype(int)
y = df.churned
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)

pre = ColumnTransformer([("cat", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), CAT),
                         ("num", StandardScaler(), NUM + BOOL)])
models = {
    "Logistic Regression": Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced"))]),
    "Gradient Boosting": Pipeline([("pre", pre), ("clf", GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=SEED))]),
}
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
perf = []
probs = {}
for name, m in models.items():
    cv_auc = cross_val_score(m, Xtr, ytr, cv=cv, scoring="roc_auc")
    m.fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    probs[name] = p
    thr = 0.5
    pred = (p >= thr).astype(int)
    perf.append(dict(model=name, cv_auc_mean=round(cv_auc.mean(), 3), cv_auc_std=round(cv_auc.std(), 3),
                     test_auc=round(roc_auc_score(yte, p), 3), precision=round(precision_score(yte, pred), 3),
                     recall=round(recall_score(yte, pred), 3), f1=round(f1_score(yte, pred), 3)))
perf = pd.DataFrame(perf)
perf.to_csv(OUT / "model_performance.csv", index=False)

# Odds ratios from the logistic model (interpretable drivers)
lr = models["Logistic Regression"]
names = lr.named_steps["pre"].get_feature_names_out()
coef = lr.named_steps["clf"].coef_[0]
odds = (pd.DataFrame({"feature": [n.split("__", 1)[1] for n in names], "coefficient": coef})
          .assign(odds_ratio=lambda d: np.exp(d.coefficient).round(2))
          .sort_values("coefficient", ascending=False))
odds["coefficient"] = odds.coefficient.round(3)
odds.to_csv(OUT / "logistic_odds_ratios.csv", index=False)

gb = models["Gradient Boosting"]
gnames = [n.split("__", 1)[1] for n in gb.named_steps["pre"].get_feature_names_out()]
imp = (pd.DataFrame({"feature": gnames, "importance": gb.named_steps["clf"].feature_importances_})
         .sort_values("importance", ascending=False).head(15))
imp["importance"] = imp.importance.round(4)
imp.to_csv(OUT / "gb_feature_importance.csv", index=False)

# ---------- 3. Gains / lift by decile (best model, test set) ----------
best = perf.sort_values("test_auc", ascending=False).iloc[0].model
p = probs[best]
g = pd.DataFrame({"score": p, "churned": yte.values}).sort_values("score", ascending=False)
g["decile"] = np.repeat(np.arange(1, 11), int(np.ceil(len(g) / 10)))[: len(g)]
gains = g.groupby("decile").agg(customers=("churned", "size"), churners=("churned", "sum"), avg_score=("score", "mean"))
gains["churn_rate_pct"] = (100 * gains.churners / gains.customers).round(1)
gains["cum_pct_churners_captured"] = (100 * gains.churners.cumsum() / gains.churners.sum()).round(1)
gains["lift"] = (gains.churn_rate_pct / (100 * yte.mean())).round(2)
gains["avg_score"] = gains.avg_score.round(3)
gains.reset_index().to_csv(OUT / "gains_by_decile.csv", index=False)

# Confusion matrix of best model at 0.5
tn, fp, fn, tp = confusion_matrix(yte, (p >= 0.5).astype(int)).ravel()

# ---------- 4. Score every customer for the retention team ----------
best_model = models[best].fit(X, y)  # refit on all data for scoring
df["churn_risk_score"] = best_model.predict_proba(X)[:, 1].round(3)
df["risk_tier"] = pd.cut(df.churn_risk_score, [-0.01, 0.3, 0.6, 1.0], labels=["Low", "Medium", "High"])
active = df[df.churned == 0]
tiers = (active.groupby("risk_tier", observed=True)
               .agg(customers=("customer_id", "size"), mrr=("monthly_charges", "sum"))
               .round(0).reset_index())
tiers.to_csv(OUT / "active_customers_by_risk_tier.csv", index=False)
(active.sort_values("churn_risk_score", ascending=False)
       [["customer_id", "contract", "tenure_months", "InternetService", "payment_method", "monthly_charges", "churn_risk_score", "risk_tier"]]
       .head(500).to_csv(OUT / "retention_target_list_top500.csv", index=False))
df[["customer_id", "churn_risk_score", "risk_tier"]].to_csv(ROOT / "powerbi" / "customer_risk_scores.csv", index=False)

summary = dict(best_model=best, test_auc=float(perf.set_index("model").loc[best, "test_auc"]),
               top3_deciles_capture=float(gains.cum_pct_churners_captured.iloc[2]),
               top_decile_lift=float(gains.lift.iloc[0]), confusion=dict(tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp)))
(OUT / "model_summary.json").write_text(json.dumps(summary, indent=2))
print(perf.to_string(index=False)); print(stats.head(8).to_string(index=False))
print(odds.head(8).to_string(index=False)); print(odds.tail(6).to_string(index=False))
print(gains.to_string()); print(tiers.to_string()); print(summary)
