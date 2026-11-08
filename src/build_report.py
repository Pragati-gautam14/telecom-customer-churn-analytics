"""README charts (outputs/charts) + interactive dashboard (docs/index.html)."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from viz import C, SEQ, INK, INK2, plt, save, style_fig, dashboard, table_html

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs" / "tables"; CH = ROOT / "outputs" / "charts"; CH.mkdir(parents=True, exist_ok=True)
REPO = "https://github.com/Pragati-gautam14/telecom-customer-churn-analytics"
rd = lambda n: pd.read_csv(T / f"{n}.csv")
k = rd("headline_kpis").iloc[0]
dim = rd("churn_by_dimension")
rm = rd("risk_matrix")
odds = rd("logistic_odds_ratios")
gains = rd("gains_by_decile")
perf = rd("model_performance")
tiers = rd("active_customers_by_risk_tier")
segs = rd("top_risk_segments")
ms = json.loads((T / "model_summary.json").read_text())

ORD = {"Contract": ["Month-to-month", "One year", "Two year"],
       "Tenure band": ["0-6 m", "7-12 m", "13-24 m", "25-48 m", "49-72 m"],
       "Internet service": ["Fiber optic", "DSL", "No"],
       "Payment method": ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
       "Add-on services": [str(i) for i in range(7)]}
get = lambda d: dim[dim.dimension == d].set_index("value").loc[ORD[d]].reset_index()
avg = k.churn_rate_pct

# ---------- PNGs ----------
fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), sharey=True)
for ax, d in zip(axes, ["Contract", "Tenure band", "Internet service", "Payment method"]):
    s = get(d)
    lbl = [v.replace(" (automatic)", "\n(auto)") for v in s.value]
    ax.bar(lbl, s.churn_rate_pct, color=C[0], width=0.6)
    ax.axhline(avg, color=INK2, ls="--", lw=0.9)
    for i, v in enumerate(s.churn_rate_pct):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9, color=INK)
    ax.set_title(d, fontsize=11); ax.tick_params(axis="x", labelsize=8, rotation=0); ax.grid(axis="x", visible=False)
axes[0].set_ylabel("Churn rate %")
fig.suptitle(f"Churn rate by driver (dashed line = {avg}% average)", x=0.01, ha="left", fontweight="bold", color=INK)
save(fig, CH / "01_churn_by_driver.png")

pv = rm.pivot(index="contract", columns="tenure_band", values="churn_rate_pct").reindex(index=ORD["Contract"], columns=ORD["Tenure band"])
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("b", SEQ)
fig, ax = plt.subplots(figsize=(9, 3.2))
ax.imshow(pv.values, cmap=cmap, aspect="auto", vmin=0, vmax=60)
ax.set_xticks(range(5), pv.columns); ax.set_yticks(range(3), pv.index); ax.grid(False)
for i in range(3):
    for j in range(5):
        v = pv.values[i, j]; ax.text(j, i, f"{v:.0f}%", ha="center", va="center", color="white" if v > 35 else INK)
ax.set_title("Churn risk matrix: contract × tenure"); ax.set_xlabel("Tenure")
save(fig, CH / "02_risk_matrix.png")

o = pd.concat([odds.head(7), odds.tail(6)]).sort_values("coefficient")
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(o.feature, o.odds_ratio - 1, left=1, color=[C[1] if v > 1 else C[0] for v in o.odds_ratio], height=0.6)
ax.axvline(1, color=INK2, lw=1); ax.grid(axis="y", visible=False)
ax.set_xlabel("Odds ratio (per category vs. baseline / per 1 SD for numeric)")
ax.set_title("Logistic regression drivers: >1 raises churn odds, <1 lowers them")
save(fig, CH / "03_odds_ratios.png")

fig, ax = plt.subplots(figsize=(8, 4))
xs = [0] + list(gains.decile * 10); ys = [0] + list(gains.cum_pct_churners_captured)
ax.plot(xs, ys, color=C[0], lw=2, marker="o", ms=5, label="Model")
ax.plot([0, 100], [0, 100], color=INK2, ls="--", lw=1, label="Random targeting")
ax.annotate(f"Top 30% → {ys[3]:.0f}% of churners", (30, ys[3]), (42, ys[3] - 22), arrowprops=dict(arrowstyle="->", color=INK2))
ax.set_xlabel("% of customers contacted (highest risk first)"); ax.set_ylabel("% of churners captured")
ax.legend(frameon=False); ax.set_title(f"Cumulative gains — {ms['best_model']} (test AUC {ms['test_auc']:.2f})")
save(fig, CH / "04_gains_curve.png")

# ---------- Dashboard ----------
f1 = make_subplots(rows=1, cols=4, shared_yaxes=True, subplot_titles=["Contract", "Tenure", "Internet", "Payment"], horizontal_spacing=0.04)
for i, d in enumerate(["Contract", "Tenure band", "Internet service", "Payment method"], 1):
    s = get(d)
    f1.add_trace(go.Bar(x=[v.replace(" (automatic)", " (auto)") for v in s.value], y=s.churn_rate_pct, marker_color=C[0],
                        customdata=np.c_[s.customers, s.churned, s.churned_mrr],
                        hovertemplate="<b>%{x}</b><br>Churn %{y}%<br>%{customdata[1]:,.0f} of %{customdata[0]:,} customers<br>MRR lost $%{customdata[2]:,.0f}<extra></extra>",
                        showlegend=False), 1, i)
f1.add_hline(y=avg, line_dash="dash", line_color=INK2, line_width=1)
f1.update_yaxes(ticksuffix="%", row=1, col=1)
f1.update_annotations(font_size=12)

f2 = go.Figure(go.Heatmap(z=pv.values, x=pv.columns, y=pv.index, colorscale=[[i / 6, c] for i, c in enumerate(SEQ)],
                          zmin=0, zmax=60, xgap=2, ygap=2, text=[[f"{v:.0f}%" for v in r] for r in pv.values],
                          texttemplate="%{text}", hovertemplate="%{y}, tenure %{x}<br>Churn %{z}%<extra></extra>",
                          colorbar=dict(ticksuffix="%", thickness=10)))
f2.update_yaxes(autorange="reversed", showgrid=False)

s = get("Add-on services")
f3 = go.Figure(go.Bar(x=s.value, y=s.churn_rate_pct, marker_color=C[0], customdata=s.customers,
                      hovertemplate="%{x} add-on services<br>Churn %{y}%<br>%{customdata:,} customers<extra></extra>"))
f3.update_yaxes(ticksuffix="%"); f3.update_xaxes(title="Number of add-on services (0 includes phone-only customers)")

f4 = go.Figure(go.Bar(y=o.feature, x=o.odds_ratio - 1, base=1, orientation="h",
                      marker_color=[C[1] if v > 1 else C[0] for v in o.odds_ratio],
                      hovertemplate="%{y}<br>Odds ratio %{customdata:.2f}<extra></extra>", customdata=o.odds_ratio))
f4.add_vline(x=1, line_color=INK2, line_width=1)

f5 = go.Figure([go.Scatter(x=xs, y=ys, mode="lines+markers", name="Model", line=dict(color=C[0], width=2), marker=dict(size=8),
                           hovertemplate="Contact top %{x}%<br>Capture %{y}% of churners<extra></extra>"),
                go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Random", line=dict(color=INK2, dash="dash", width=1), hoverinfo="skip")])
f5.update_xaxes(ticksuffix="%", title="% of customers contacted"); f5.update_yaxes(ticksuffix="%")

for f, h in [(f1, 330), (f2, 260), (f3, 300), (f4, 400), (f5, 330)]:
    style_fig(f, h)
f1.update_layout(margin=dict(l=10, r=10, t=30, b=10))

seg_t = segs.rename(columns={"contract": "Contract", "internet_service": "Internet", "payment_method": "Payment",
                             "customers": "Customers", "churned": "Churned", "churn_rate_pct": "Churn %", "churned_mrr": "MRR lost ($)"})
seg_t["Churned"] = seg_t.Churned.astype(int); seg_t["MRR lost ($)"] = seg_t["MRR lost ($)"].map("{:,.0f}".format)
perf_t = perf.rename(columns={"model": "Model", "cv_auc_mean": "CV AUC", "test_auc": "Test AUC", "precision": "Precision", "recall": "Recall", "f1": "F1"})[["Model", "CV AUC", "Test AUC", "Precision", "Recall", "F1"]]
hi = tiers.set_index("risk_tier").loc["High"]
mtm = get("Contract").iloc[0]; fib = get("Internet service").iloc[0]; ec = get("Payment method").iloc[0]; t6 = get("Tenure band").iloc[0]
top = segs.iloc[0]
insights = [
    f"<b>Churn costs ${k.churned_mrr/1e3:,.0f}K of monthly revenue</b> ({k.mrr_churn_pct}% of MRR, ≈${k.annualised_revenue_lost/1e6:.2f}M a year). Churners pay more (${k.avg_bill_churners:.0f} vs ${k.avg_bill_retained:.0f} a month), so revenue churn is higher than customer churn ({k.churn_rate_pct}%).",
    f"<b>Contract type is the strongest driver:</b> month-to-month customers churn at {mtm.churn_rate_pct:.0f}% vs 3% on two-year contracts, and make up {mtm.share_of_churners_pct:.0f}% of all churners → incentivise annual upgrades.",
    f"<b>The first 6 months are critical:</b> {t6.churn_rate_pct:.0f}% of new customers leave in that window → onboarding and early check-in calls.",
    f"<b>Highest-risk segment:</b> month-to-month + fiber optic + electronic check: {int(top.customers):,} customers with {top.churn_rate_pct:.0f}% churn (${top.churned_mrr/1e3:,.0f}K MRR lost). Fiber churn ({fib.churn_rate_pct:.0f}%) points to a price/quality issue worth investigating.",
    f"<b>Support add-ons protect revenue:</b> churn falls from 46% with 1 add-on to 5% with 6. Customers without tech support churn at 42% vs 15% with it → bundle tech support and online security.",
    f"<b>Targeting model:</b> {ms['best_model']} (test AUC {ms['test_auc']:.2f}). Contacting the top 30% of customers by risk score reaches <b>{ms['top3_deciles_capture']:.0f}% of churners</b>, 2.2× better than random. {int(hi.customers):,} active customers are flagged high-risk (${hi.mrr/1e3:,.0f}K MRR).",
]
dashboard("Telecom Customer Churn Analytics",
          "7,043 telecom customers · churn drivers, revenue at risk and a churn-prediction model",
          [("Customers", f"{int(k.customers):,}", ""), ("Churn rate", f"{k.churn_rate_pct}%", f"{int(k.churned_customers):,} customers"),
           ("MRR lost", f"${k.churned_mrr/1e3:,.0f}K", f"{k.mrr_churn_pct}% of MRR"), ("Annualised loss", f"${k.annualised_revenue_lost/1e6:.2f}M", ""),
           ("Model AUC", f"{ms['test_auc']:.2f}", ms["best_model"]), ("Top-30% capture", f"{ms['top3_deciles_capture']:.0f}%", "of churners")],
          [("Churn rate by key driver", f"Dashed line = {avg}% overall churn. Hover for customer counts and MRR lost.", f1, "full"),
           ("Risk matrix: contract × tenure", "Churn % for each contract and tenure group", f2, "half"),
           ("Add-on services vs churn", "More support and protection services lead to lower churn", f3, "half"),
           ("What drives churn: logistic regression odds ratios", "Orange raises churn odds, blue lowers them (numeric features per 1 SD)", f4, "half"),
           ("Cumulative gains: who to call first", "Share of churners reached by contacting customers in order of risk score", f5, "half"),
           ("Highest-risk segments (100+ customers)", "Contract × internet × payment combinations ranked by churn rate", table_html(seg_t, ["Customers", "Churned", "Churn %", "MRR lost ($)"]), "full"),
           ("Model comparison", "5-fold cross-validated AUC on the training set and hold-out test metrics (threshold 0.5)", table_html(perf_t, ["CV AUC", "Test AUC", "Precision", "Recall", "F1"]), "full")],
          ROOT / "docs" / "index.html", REPO, insights)
print("ok", hi.to_dict(), mtm.share_of_churners_pct)
