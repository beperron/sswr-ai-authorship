"""
ESL-bias proxy: stratify by first-author country of affiliation.

Per RAID 2024 / Liang et al. 2023, AI-text detectors show elevated FPR on
non-native English writers.  We do NOT have first-author native language;
we proxy with country of first-author affiliation (US-based vs not).

Output: per-cohort time series of detector outcomes; pre/post test;
year-clustered DiD on US vs non-US first authors.
"""

import pandas as pd, numpy as np, json
from pathlib import Path
import statsmodels.api as sm

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
RES  = ROOT / "results"

# Load and merge
auth = pd.read_csv(ROOT / "data" / "sswr_paper_authors.csv", dtype=str, keep_default_na=False)
firsts = auth[auth["author_order"]=="1"][["paper_id","country_normalized"]].drop_duplicates("paper_id")
firsts.columns = ["id","fa_country"]
df = pd.read_pickle(ROOT / "data" / "scores_labeled.pkl")
df["score_primary"] = pd.to_numeric(df["score_primary"], errors="coerce")
df["label_binary"] = pd.to_numeric(df["label_binary"], errors="coerce")
df = df.merge(firsts, on="id", how="left")
print(f"N = {len(df):,}; missing fa_country = {df['fa_country'].isna().sum()}")

# US-vs-non-US (the RAID-most-relevant axis)
df["fa_us"] = (df["fa_country"].str.upper().isin(["US","USA","UNITED STATES"])).astype(int)
df["fa_us"].loc[df["fa_country"].isna() | (df["fa_country"]=="")] = np.nan
print(f"US-affiliated first authors: {df['fa_us'].sum():,.0f} "
      f"({df['fa_us'].mean()*100:.1f}% of papers with country)")
print(f"Top non-US countries:")
print(df[df["fa_us"]==0]["fa_country"].value_counts().head(10).to_string())

# Per-year cohort table
df_cl = df[df["fa_us"].notna()].copy()
df_cl["fa_us_lab"] = np.where(df_cl["fa_us"]==1, "US", "non-US")
agg = df_cl.groupby(["year","fa_us_lab"]).agg(
    n=("score_primary","size"),
    mean_score=("score_primary","mean"),
    pct_binary=("label_binary","mean"),
).reset_index()
agg.to_csv(RES / "country_yearly.csv", index=False)
print("\nPer-year by US/non-US (head + tail):")
print(agg.head(8).round(4).to_string(index=False))
print("...")
print(agg.tail(8).round(4).to_string(index=False))

# Pre vs post (mature LLM = 2025+)
df_cl["period"] = np.where(df_cl["year"]>=2025, "post", "pre")
piv = df_cl.groupby(["fa_us_lab","period"])[["score_primary","label_binary"]].mean().round(4)
print("\nMean score and binary % by US/non-US × period:")
print(piv.to_string())

# Diagnostic: pre-LLM baseline difference (CRITICAL for ESL bias)
pre = df_cl[(df_cl["year"]>=2009) & (df_cl["year"]<=2017)]
us_pre = pre[pre["fa_us"]==1]
nus_pre = pre[pre["fa_us"]==0]
from scipy.stats import ttest_ind
t = ttest_ind(us_pre["score_primary"], nus_pre["score_primary"], equal_var=False)
print(f"\nPRE-LLM baseline (2009-2017) ESL bias diagnostic:")
print(f"  US-affiliated  (N={len(us_pre):,}):  mean={us_pre['score_primary'].mean():.4f}, P95-rate={us_pre['label_binary'].mean()*100:.2f}%")
print(f"  non-US (N={len(nus_pre):,}):  mean={nus_pre['score_primary'].mean():.4f}, P95-rate={nus_pre['label_binary'].mean()*100:.2f}%")
print(f"  Welch t={t.statistic:.2f}, p={t.pvalue:.2e}")
print(f"  -> Δ = {nus_pre['score_primary'].mean() - us_pre['score_primary'].mean():+.4f}")

# DiD: does the post-period jump differ between US and non-US first authors?
df_cl["post"] = (df_cl["period"]=="post").astype(int)
df_cl["nonus"] = 1 - df_cl["fa_us"]
df_cl["nonus_post"] = df_cl["nonus"] * df_cl["post"]
out = {}
for outcome in ["score_primary","label_binary"]:
    X = sm.add_constant(df_cl[["post","nonus","nonus_post"]])
    mod = sm.OLS(df_cl[outcome], X).fit(cov_type="cluster", cov_kwds={"groups": df_cl["year"].values})
    print(f"\nDiD ({outcome}):")
    print(mod.summary().tables[1])
    out[outcome] = {
        "params": mod.params.round(6).to_dict(),
        "pvalues": mod.pvalues.round(6).to_dict(),
    }

# Save
results = {
    "esl_baseline_diagnostic": {
        "us_pre_mean": float(us_pre["score_primary"].mean()),
        "nonus_pre_mean": float(nus_pre["score_primary"].mean()),
        "delta": float(nus_pre["score_primary"].mean() - us_pre["score_primary"].mean()),
        "welch_t": float(t.statistic), "p": float(t.pvalue),
        "us_pre_pct_p95": float(us_pre["label_binary"].mean()),
        "nonus_pre_pct_p95": float(nus_pre["label_binary"].mean()),
        "interpretation": ("Positive delta = non-US first authors score higher in pre-LLM era, "
                           "i.e., known ESL detector bias is present in this corpus.")
    },
    "DiD_year_clustered": out,
}
(RES / "country_did.json").write_text(json.dumps(results, indent=2, default=str))
print(f"\nSaved -> {RES / 'country_did.json'}")
