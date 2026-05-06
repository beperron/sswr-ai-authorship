"""
Step 9 — Qualitative vs quantitative comparison.

User instruction: 'Show a difference between qualitative and quantitative.'
We compare per-year detector outcomes between methodology=='qualitative' and
methodology=='quantitative' cohorts. Reviews and mixed_methods are reported
descriptively but not stratified.
"""

import pandas as pd, numpy as np, json
from pathlib import Path
import statsmodels.api as sm

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
df = pd.read_pickle(ROOT / "data" / "scores_labeled.pkl")
df["score_primary"] = pd.to_numeric(df["score_primary"], errors="coerce")
df["label_binary"] = pd.to_numeric(df["label_binary"], errors="coerce")

# Per-year, per-cohort aggregates
def agg_one(d):
    return pd.Series({
        "n": len(d),
        "mean_score": d["score_primary"].mean(),
        "pct_binary": d["label_binary"].mean(),
        "pct_ai_edited_or_ai": (d["label_ternary"] != "human").mean(),
    })
agg = df[df["methodology"].isin(["qualitative","quantitative"])] \
    .groupby(["year","methodology"]).apply(agg_one, include_groups=False).reset_index()
agg.to_csv(ROOT / "results" / "qual_vs_quant_yearly.csv", index=False)
print(agg.to_string(index=False))

# Difference test pre vs post: simple two-way comparison
# Period: pre = conf years 2005-2024 (pre-mature-LLM), post = 2025-2026
df["period"] = np.where(df["year"] >= 2025, "post", "pre")
df_qq = df[df["methodology"].isin(["qualitative","quantitative"])].copy()

print("\nMean score by period x methodology:")
print(df_qq.groupby(["period","methodology"])["score_primary"].mean().round(4).unstack().to_string())

print("\nProportion >= P95 (binary AI) by period x methodology:")
print(df_qq.groupby(["period","methodology"])["label_binary"].mean().round(4).unstack().to_string())

# Difference-in-differences via OLS with HC robust SEs
df_qq["post"] = (df_qq["period"] == "post").astype(int)
df_qq["qual"] = (df_qq["methodology"] == "qualitative").astype(int)
df_qq["qual_post"] = df_qq["post"] * df_qq["qual"]
out = {}
for outcome in ["score_primary", "label_binary"]:
    X = sm.add_constant(df_qq[["post", "qual", "qual_post"]])
    mod = sm.OLS(df_qq[outcome], X).fit(cov_type="HC3")
    print(f"\nDiD ({outcome}):")
    print(mod.summary().tables[1])
    out[outcome] = {
        "params": mod.params.round(6).to_dict(),
        "pvalues": mod.pvalues.round(6).to_dict(),
        "did_coef_qual_post": float(mod.params["qual_post"]),
        "did_p_qual_post": float(mod.pvalues["qual_post"]),
    }
(ROOT / "results" / "qual_vs_quant_did.json").write_text(json.dumps(out, indent=2, default=str))
print(f"\nSaved -> {ROOT / 'results' / 'qual_vs_quant_did.json'}")
