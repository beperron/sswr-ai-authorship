"""
Step 11 — Robustness pack addressing peer-review punch list:

  R1. ITS re-centered at intervention; level-change-at-intervention via linear
      combination test (peer review item B/2).
  R2. Logit-transformed score sensitivity (item A/1, 18).
  R3. Sensitivity excluding 2026 conference (item 16).
  R4. Qual-vs-quant DiD with year-clustered SEs (item F/10).
  R5. Year-clustered SE for fa_rank DiD (item E).
  R6. Fa_rank merge assertions (item E/6,7).
  R7. Pre-period mean_score gentle drift quantified (item D/5).
"""

import pandas as pd, numpy as np, json
import statsmodels.api as sm
from pathlib import Path

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
OUT  = ROOT / "results" / "robustness.json"
df = pd.read_pickle(ROOT / "data" / "scores_labeled.pkl")
df["score_primary"] = pd.to_numeric(df["score_primary"], errors="coerce")
df["label_binary"]  = pd.to_numeric(df["label_binary"], errors="coerce")
preproc = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl")
if "fa_rank" not in df.columns:
    n0 = len(df)
    df = df.merge(preproc[["id","fa_rank"]], on="id", how="left")
    assert len(df) == n0, f"Row count changed: {n0} -> {len(df)}"
    assert df["fa_rank"].notna().all(), "Missing fa_rank after merge"

agg = pd.read_csv(ROOT / "results" / "yearly_aggregates.csv")
report = {}

# ---------- R1. Re-centered ITS with linear combination test ----------
def its_recentered(y, intervention=2025, label="outcome"):
    """T centered at intervention, so I_post is the level change AT intervention."""
    y = np.asarray(y, dtype=float)
    yrs = agg["year"].values.astype(float)
    T = yrs - intervention
    I = (yrs >= intervention).astype(float)
    X = np.column_stack([np.ones_like(T), T, I, T*I])
    Xn = pd.DataFrame(X, columns=["const","T","I","TxI"])
    mod = sm.OLS(y, Xn).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    out = {
        "label": label,
        "intervention_year": intervention,
        "intercept": float(mod.params["const"]),
        "pre_slope_per_yr": float(mod.params["T"]),
        "level_change_at_intervention": float(mod.params["I"]),
        "level_change_p": float(mod.pvalues["I"]),
        "level_change_99CI": [float(mod.conf_int(.01).loc["I", 0]),
                              float(mod.conf_int(.01).loc["I", 1])],
        "slope_change_per_yr": float(mod.params["TxI"]),
        "slope_change_p": float(mod.pvalues["TxI"]),
        "post_slope_per_yr": float(mod.params["T"] + mod.params["TxI"]),
    }
    return out

print("R1 — ITS re-centered at 2025 intervention:")
for col, lab in [("mean_score","mean_score"),
                 ("pct_binary","pct_binary"),
                 ("pct_ai_edited_or_ai","pct_ai_edited_or_ai")]:
    r = its_recentered(agg[col].values, 2025, lab)
    print(f"  {lab}: level Δ={r['level_change_at_intervention']:+.4f} "
          f"(99% CI {r['level_change_99CI'][0]:+.4f}, {r['level_change_99CI'][1]:+.4f}, "
          f"p={r['level_change_p']:.2e})  "
          f"slope Δ={r['slope_change_per_yr']:+.4f}/yr (p={r['slope_change_p']:.2e})")
    report.setdefault("R1_ITS_recentered", {})[lab] = r

# ---------- R2. Logit-transformed score sensitivity ----------
print("\nR2 — Logit-transformed score sensitivity:")
EPS = 1e-6
df["logit_score"] = np.log((df["score_primary"].clip(EPS, 1-EPS)) /
                           (1 - df["score_primary"].clip(EPS, 1-EPS)))
agg_l = df.groupby("year")["logit_score"].agg(["mean","median","std"]).reset_index()
agg_l.columns = ["year","logit_mean","logit_median","logit_sd"]
agg_l.to_csv(ROOT / "results" / "yearly_aggregates_logit.csv", index=False)
r = its_recentered(agg_l["logit_mean"].values, 2025, "logit_mean")
# Need to use agg_l instead of agg; quick re-fit
yrs = agg_l["year"].values.astype(float)
T = yrs - 2025
I = (yrs >= 2025).astype(float)
X = np.column_stack([np.ones_like(T), T, I, T*I])
Xn = pd.DataFrame(X, columns=["const","T","I","TxI"])
mod = sm.OLS(agg_l["logit_mean"].values.astype(float), Xn).fit(cov_type="HAC", cov_kwds={"maxlags":2})
print(f"  logit_mean: level Δ={mod.params['I']:+.4f}, p={mod.pvalues['I']:.2e}; "
      f"slope Δ={mod.params['TxI']:+.4f}/yr, p={mod.pvalues['TxI']:.2e}")
print(agg_l.round(3).to_string(index=False))
report["R2_logit_sensitivity"] = {
    "intercept_at_intervention": float(mod.params["const"]),
    "level_change": float(mod.params["I"]),
    "level_change_p": float(mod.pvalues["I"]),
    "slope_change": float(mod.params["TxI"]),
    "slope_change_p": float(mod.pvalues["TxI"]),
    "yearly_logit_means": agg_l.set_index("year")["logit_mean"].round(4).to_dict(),
    "interpretation": ("Logit-transformed mean score is unbounded; if the original-scale "
                       "result is driven purely by detector saturation, the logit version "
                       "should be much weaker."),
}

# ---------- R3. Sensitivity excluding 2026 ----------
print("\nR3 — ITS excluding 2026 cycle:")
agg_no26 = agg[agg["year"] <= 2025].reset_index(drop=True)
def its_recentered_v(agg_v, y, intervention, label):
    y = np.asarray(y, dtype=float)
    yrs = agg_v["year"].values.astype(float)
    T = yrs - intervention
    I = (yrs >= intervention).astype(float)
    X = np.column_stack([np.ones_like(T), T, I, T*I])
    Xn = pd.DataFrame(X, columns=["const","T","I","TxI"])
    mod = sm.OLS(y, Xn).fit(cov_type="HAC", cov_kwds={"maxlags":2})
    return {
        "label": label,
        "level_change": float(mod.params["I"]),
        "level_change_p": float(mod.pvalues["I"]),
        "slope_change_per_yr": float(mod.params["TxI"]),
        "slope_change_p": float(mod.pvalues["TxI"]),
    }
report["R3_excluding_2026"] = {}
for col in ["mean_score","pct_binary","pct_ai_edited_or_ai"]:
    r = its_recentered_v(agg_no26, agg_no26[col].values, 2025, col)
    print(f"  {col}: level Δ={r['level_change']:+.4f} (p={r['level_change_p']:.2e})  "
          f"slope Δ={r['slope_change_per_yr']:+.4f}/yr (p={r['slope_change_p']:.2e})")
    report["R3_excluding_2026"][col] = r

# ---------- R4. Qual-vs-quant DiD with year-clustered SEs ----------
print("\nR4 — Qual-vs-quant DiD with year-clustered SEs:")
df["period"] = np.where(df["year"] >= 2025, "post", "pre")
qq = df[df["methodology"].isin(["qualitative","quantitative"])].copy()
qq["post"] = (qq["period"] == "post").astype(int)
qq["qual"] = (qq["methodology"] == "qualitative").astype(int)
qq["qual_post"] = qq["post"] * qq["qual"]
report["R4_qualquant_year_clustered"] = {}
for outcome in ["score_primary","label_binary"]:
    X = sm.add_constant(qq[["post","qual","qual_post"]])
    mod = sm.OLS(qq[outcome], X).fit(cov_type="cluster",
                                     cov_kwds={"groups": qq["year"].values})
    print(f"  {outcome}: qual_post β={mod.params['qual_post']:+.4f} (clustered SE={mod.bse['qual_post']:.4f}, p={mod.pvalues['qual_post']:.4f})")
    report["R4_qualquant_year_clustered"][outcome] = {
        "qual_post_beta": float(mod.params["qual_post"]),
        "qual_post_se":   float(mod.bse["qual_post"]),
        "qual_post_p":    float(mod.pvalues["qual_post"]),
        "post_beta":      float(mod.params["post"]),
        "post_p":         float(mod.pvalues["post"]),
    }

# ---------- R5. Fa_rank DiD with year-clustered SEs ----------
print("\nR5 — Fa_rank DiD with year-clustered SEs (academic ranks only; 'other' excluded):")
ACADEMIC = ["assistant","associate","full","postdoc","doctoral"]
fa = df[df["fa_rank"].isin(ACADEMIC)].copy()
fa["post"] = (fa["period"] == "post").astype(int)
for r in [x for x in ACADEMIC if x != "assistant"]:
    fa[f"r_{r}"] = (fa["fa_rank"]==r).astype(int)
    fa[f"r_{r}_post"] = fa[f"r_{r}"] * fa["post"]
cols = ["post"] + [f"r_{r}" for r in ACADEMIC if r!="assistant"] + \
       [f"r_{r}_post" for r in ACADEMIC if r!="assistant"]
report["R5_farank_year_clustered"] = {}
for outcome in ["score_primary","label_binary"]:
    X = sm.add_constant(fa[cols])
    mod = sm.OLS(fa[outcome], X).fit(cov_type="cluster",
                                     cov_kwds={"groups": fa["year"].values})
    rank_post = {k: float(mod.params[f"r_{k}_post"]) for k in ACADEMIC if k!="assistant"}
    rank_post_p = {k: float(mod.pvalues[f"r_{k}_post"]) for k in ACADEMIC if k!="assistant"}
    print(f"  {outcome}: post (assistant ref) = {mod.params['post']:+.4f} "
          f"(clustered SE={mod.bse['post']:.4f}, p={mod.pvalues['post']:.4f})")
    for k,v in rank_post.items():
        print(f"    r_{k}_post = {v:+.4f}  p={rank_post_p[k]:.4f}")
    report["R5_farank_year_clustered"][outcome] = {
        "assistant_post_beta": float(mod.params["post"]),
        "assistant_post_p":    float(mod.pvalues["post"]),
        "differential_post_beta": rank_post,
        "differential_post_p":    rank_post_p,
    }

# ---------- R7. Pre-period drift quantification ----------
pre = agg[(agg["year"]>=2009) & (agg["year"]<=2017)]
slopes = {}
for col in ["mean_score","pct_binary","pct_ai_edited_or_ai"]:
    s, _ = np.polyfit(pre["year"]-2013, pre[col].values.astype(float), 1)
    slopes[col] = float(s)
report["R7_within_calibration_drift"] = {
    "slopes_per_year_2009_2017": slopes,
    "interpretation": ("Mean continuous score has a small positive drift even within "
                       "the calibration window (~+0.005/yr), explaining the placebo p=0.003 "
                       "for mean_score. The discrete proportions are more robust.")
}

OUT.write_text(json.dumps(report, indent=2, default=str))
print(f"\nSaved -> {OUT}")
