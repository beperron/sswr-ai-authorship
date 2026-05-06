"""
Main analysis script. Computes the Stage 2 numbers reported in the manuscript:
P95 thresholds on the locked 2010-2017 calibration window, yearly above-threshold
proportions, the H1 segmented-regression step at conf 2025, Cohen's kappa
between detectors, and Pearson r between continuous detector scores. Uses the
academic-tuned desklib variant (desklib/ai-text-detector-academic-v1.01) as
the cross-family detector, per Deviation 9 in logs/PROTOCOL_DEVIATIONS.md.

Reads:
  data/scores_editlens_roberta.pkl       (EditLens RoBERTa-large; primary; unchanged)
  data/scores_editlens_llama.pkl         (EditLens Llama-3.2-3B; secondary; unchanged)
  data/scores_primary_academic.pkl       (NEW: academic-tuned desklib)
  data/scores_editlens_roberta_mw.pkl    (multi-window; unchanged)
  data/writing_quality.pkl               (unchanged)
  data/corpus_preprocessed.pkl           (rank metadata)
  data/sswr_paper_authors.csv            (country)

Writes:
  results/main_analysis_results.json   (all numbers for manuscript)
"""

import pandas as pd, numpy as np, json
import statsmodels.api as sm
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
RES  = ROOT / "results"

CAL_LO, CAL_HI = 2010, 2017
ANALYTIC_LO    = 2010

# ---- Load ----
edl_r = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta.pkl")[
    ["id","year","methodology","text_wc","score_editlens","bucket_editlens"]]
edl_l = pd.read_pickle(ROOT/"data"/"scores_editlens_llama.pkl")[
    ["id","score_editlens_llama","bucket_editlens_llama"]]
desk  = pd.read_pickle(ROOT/"data"/"scores_primary_academic.pkl")[["id","score_primary"]]
desk = desk.rename(columns={"score_primary": "score_desklib_academic"})
mw    = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta_mw.pkl")[
    ["id","score_editlens_mw","bucket_editlens_mw","n_windows"]]
wq    = pd.read_pickle(ROOT/"data"/"writing_quality.pkl").reset_index()
preproc = pd.read_pickle(ROOT/"data"/"corpus_preprocessed.pkl")[["id","fa_rank"]]
auth  = pd.read_csv(ROOT/"data"/"sswr_paper_authors.csv",
                    dtype=str, keep_default_na=False)

US_SET    = {"USA","US","UNITED STATES","UNITED STATES OF AMERICA"}
OTHER_ANG = {"CANADA","UNITED KINGDOM","UK","GREAT BRITAIN","ENGLAND",
             "SCOTLAND","WALES","NORTHERN IRELAND","IRELAND",
             "REPUBLIC OF IRELAND","AUSTRALIA","NEW ZEALAND"}
def cohort(c):
    if not isinstance(c, str) or c.strip()=="": return np.nan
    cu = c.strip().upper()
    if cu in US_SET:    return "US"
    if cu in OTHER_ANG: return "Other Anglophone"
    return "Non-Anglophone"

firsts = auth[auth.author_order=="1"][["paper_id","country_normalized"]].drop_duplicates("paper_id")
firsts.columns = ["id","fa_country"]

df = (edl_r.merge(edl_l, on="id")
            .merge(desk, on="id")
            .merge(mw, on="id")
            .merge(wq, on="id")
            .merge(preproc, on="id")
            .merge(firsts, on="id", how="left"))
for c in ["score_editlens","score_editlens_llama","score_desklib_academic","score_editlens_mw",
          "bucket_editlens","bucket_editlens_llama","bucket_editlens_mw"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df["fa_cohort"] = df.fa_country.map(cohort)

df = df[df.year >= ANALYTIC_LO].copy()
print(f"Analytic N (conf {ANALYTIC_LO}-2026) = {len(df):,}")

cal = df[(df.year>=CAL_LO)&(df.year<=CAL_HI)]
P95_e   = float(np.quantile(cal.score_editlens,           0.95))
P95_l   = float(np.quantile(cal.score_editlens_llama,     0.95))
P95_d   = float(np.quantile(cal.score_desklib_academic,   0.95))
P95_emw = float(np.quantile(cal.score_editlens_mw,        0.95))
print(f"\nCalibration N (conf {CAL_LO}-{CAL_HI}) = {len(cal):,}")
print(f"  P95 EditLens RoBERTa-large (single)         = {P95_e:.4f}")
print(f"  P95 EditLens RoBERTa-large (multi-window)   = {P95_emw:.4f}")
print(f"  P95 EditLens Llama-3.2-3B                   = {P95_l:.4f}")
print(f"  P95 desklib academic                        = {P95_d:.4f}")

df["bin_e"] = (df.score_editlens         >= P95_e).astype(int)
df["bin_l"] = (df.score_editlens_llama   >= P95_l).astype(int)
df["bin_d"] = (df.score_desklib_academic >= P95_d).astype(int)
df["any_e"]  = (df.bucket_editlens >= 1).astype(int)
df["full_e"] = (df.bucket_editlens == 3).astype(int)

# ---- Yearly Table ----
print("\n" + "="*70)
print("Yearly proportion above P95")
print("="*70)
yearly = df.groupby("year").agg(
    n=("id","count"),
    pct_e=("bin_e", lambda x: round(x.mean()*100, 1)),
    pct_l=("bin_l", lambda x: round(x.mean()*100, 1)),
    pct_d=("bin_d", lambda x: round(x.mean()*100, 1)),
).reset_index()
print(yearly.to_string(index=False))

# ---- H1 segmented regression (Newey-West HAC; 95% CI) ----
print("\n" + "="*70)
print("H1 segmented regression (Newey-West HAC, maxlags=2)")
print("="*70)
def its(yr, y, intervention=2025):
    yr = np.asarray(yr, dtype=float); y = np.asarray(y, dtype=float)
    T = yr - intervention
    I = (yr >= intervention).astype(float)
    X = sm.add_constant(pd.DataFrame({"T":T, "I":I, "TxI":T*I}))
    mod = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags":2})
    return {
        "level_pp": float(mod.params["I"])*100,
        "ci95_lo_pp": float(mod.conf_int(0.05).loc["I",0])*100,
        "ci95_hi_pp": float(mod.conf_int(0.05).loc["I",1])*100,
        "p":         float(mod.pvalues["I"]),
    }

yr = yearly.year.values
h1 = {}
for col, label in [("pct_e","EditLens RoBERTa-large"),
                   ("pct_l","EditLens Llama-3.2-3B"),
                   ("pct_d","desklib academic")]:
    r = its(yr, yearly[col].values/100)
    print(f"  {label:<26} step = {r['level_pp']:+.1f} pp  95% CI=[{r['ci95_lo_pp']:+.1f}, {r['ci95_hi_pp']:+.1f}]  p={r['p']:.4g}")
    h1[label] = r

# ---- H4 within-baseline (academic desklib) ----
print("\n" + "="*70)
print("H4 falsification within calibration 2010-2017")
print("="*70)
cal2 = df[(df.year>=CAL_LO)&(df.year<=CAL_HI)].copy()
cal2["log_wc"] = np.log(cal2.text_wc.astype(float).clip(lower=1))
cal2["year_centered"] = cal2.year - cal2.year.mean()
for col, label in [("score_editlens","EditLens R"), ("score_desklib_academic","desklib academic")]:
    X = sm.add_constant(cal2[["year_centered","log_wc"]])
    mod = sm.OLS(cal2[col], X).fit(cov_type="cluster", cov_kwds={"groups": cal2.year.values})
    print(f"  {label:>22}: year coef = {mod.params['year_centered']:+.4f}  p={mod.pvalues['year_centered']:.4g}")

# ---- Three-period subgroup (academic rank, methodology, country) ----
NO_EXP  = (df.year>=ANALYTIC_LO) & (df.year<=2023)
PARTIAL = (df.year==2024)
FULL    = (df.year>=2025) & (df.year<=2026)

print(f"\nCorpus by exposure period (analytic window {ANALYTIC_LO}-2026):")
print(f"  No exposure (conf {ANALYTIC_LO}-2023):  n = {NO_EXP.sum():,}")
print(f"  Partial    (conf 2024):       n = {PARTIAL.sum():,}")
print(f"  Full       (conf 2025-2026):  n = {FULL.sum():,}")

# Academic rank
print("\n" + "="*70)
print("H2 academic rank (EditLens R; desklib academic for cross-check)")
print("="*70)
RANKS = ["Postdoctoral","Full professor","Associate professor","Assistant professor","Doctoral student"]
rank_map = {"postdoc":"Postdoctoral","full":"Full professor",
            "associate":"Associate professor","assistant":"Assistant professor","doctoral":"Doctoral student"}
df["rank_label"] = df.fa_rank.map(rank_map)

print(f"\n{'Rank':<22} {'No exp':>14} {'Partial':>14} {'Full':>14}")
print("-"*68)
for r in RANKS:
    n0 = df[(df.rank_label==r) & NO_EXP];  p0 = n0.bin_e.mean()*100 if len(n0) else np.nan
    n1 = df[(df.rank_label==r) & PARTIAL]; p1 = n1.bin_e.mean()*100 if len(n1) else np.nan
    n2 = df[(df.rank_label==r) & FULL];    p2 = n2.bin_e.mean()*100 if len(n2) else np.nan
    print(f"  {r:<20} {p0:>5.1f}% (n={len(n0):,}) {p1:>5.1f}% (n={len(n1):,}) {p2:>5.1f}% (n={len(n2):,})")

print("\nDiD strict (no-exp vs full-exp; conf 2024 dropped):")
sub = df[df.rank_label.isin(["Doctoral student","Assistant professor"]) & (NO_EXP | FULL)].copy()
sub["post"] = FULL.loc[sub.index].astype(int)
sub["doc"]  = (sub.rank_label=="Doctoral student").astype(int)
sub["doc_post"] = sub.doc * sub.post
X = sm.add_constant(sub[["post","doc","doc_post"]])
mod = sm.OLS(sub.bin_e, X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
print(f"  doctoral × post (EditLens R)    = {mod.params['doc_post']*100:+.1f} pp  p={mod.pvalues['doc_post']:.4g}")
mod_d = sm.OLS(sub.bin_d, X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
print(f"  doctoral × post (desklib acad)  = {mod_d.params['doc_post']*100:+.1f} pp  p={mod_d.pvalues['doc_post']:.4g}")

# Methodology
print("\n" + "="*70)
print("H3 methodology")
print("="*70)
for m in ["qualitative","quantitative"]:
    n0 = df[(df.methodology==m) & NO_EXP];  p0 = n0.bin_e.mean()*100 if len(n0) else np.nan
    n1 = df[(df.methodology==m) & PARTIAL]; p1 = n1.bin_e.mean()*100 if len(n1) else np.nan
    n2 = df[(df.methodology==m) & FULL];    p2 = n2.bin_e.mean()*100 if len(n2) else np.nan
    print(f"  {m:<13} no-exp={p0:5.1f}% (n={len(n0):,})  partial={p1:5.1f}% (n={len(n1):,})  full={p2:5.1f}% (n={len(n2):,})")
sub = df[df.methodology.isin(["qualitative","quantitative"]) & (NO_EXP | FULL)].copy()
sub["post"] = FULL.loc[sub.index].astype(int)
sub["qual"] = (sub.methodology=="qualitative").astype(int)
sub["qual_post"] = sub.qual * sub.post
X = sm.add_constant(sub[["post","qual","qual_post"]])
mod = sm.OLS(sub.bin_e, X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
print(f"  qualitative × post (EditLens R) = {mod.params['qual_post']*100:+.1f} pp  p={mod.pvalues['qual_post']:.4g}")

# Country cohort
print("\n" + "="*70)
print("Country cohort")
print("="*70)
cdf = df[df.fa_cohort.notna()].copy()
for k in ["US","Other Anglophone","Non-Anglophone"]:
    n0 = cdf[(cdf.fa_cohort==k) & NO_EXP.loc[cdf.index]];  p0 = n0.bin_e.mean()*100 if len(n0) else np.nan
    n1 = cdf[(cdf.fa_cohort==k) & PARTIAL.loc[cdf.index]]; p1 = n1.bin_e.mean()*100 if len(n1) else np.nan
    n2 = cdf[(cdf.fa_cohort==k) & FULL.loc[cdf.index]];    p2 = n2.bin_e.mean()*100 if len(n2) else np.nan
    print(f"  {k:<18} no-exp={p0:5.1f}% (n={len(n0):,})  partial={p1:5.1f}% (n={len(n1):,})  full={p2:5.1f}% (n={len(n2):,})")
sub = cdf[NO_EXP.loc[cdf.index] | FULL.loc[cdf.index]].copy()
sub["post"]      = FULL.loc[sub.index].astype(int)
sub["other_ang"] = (sub.fa_cohort=="Other Anglophone").astype(int)
sub["non_ang"]   = (sub.fa_cohort=="Non-Anglophone").astype(int)
sub["other_ang_post"] = sub.other_ang * sub.post
sub["non_ang_post"]   = sub.non_ang   * sub.post
X = sm.add_constant(sub[["post","other_ang","non_ang","other_ang_post","non_ang_post"]])
mod = sm.OLS(sub.bin_e, X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
print(f"  Other-Ang × post = {mod.params['other_ang_post']*100:+.1f} pp  p={mod.pvalues['other_ang_post']:.4g}  CI95=[{mod.conf_int(.05).loc['other_ang_post',0]*100:+.1f}, {mod.conf_int(.05).loc['other_ang_post',1]*100:+.1f}]")
print(f"  Non-Ang   × post = {mod.params['non_ang_post']*100:+.1f} pp  p={mod.pvalues['non_ang_post']:.4g}  CI95=[{mod.conf_int(.05).loc['non_ang_post',0]*100:+.1f}, {mod.conf_int(.05).loc['non_ang_post',1]*100:+.1f}]")

# Inter-detector convergence
print("\n" + "="*70)
print("Inter-detector convergence")
print("="*70)
k_de = cohen_kappa_score(df.bin_d, df.bin_e)
k_dl = cohen_kappa_score(df.bin_d, df.bin_l)
k_el = cohen_kappa_score(df.bin_e, df.bin_l)
print(f"  Cohen kappa (desklib acad vs EditLens R) = {k_de:.3f}")
print(f"  Cohen kappa (desklib acad vs EditLens L) = {k_dl:.3f}")
print(f"  Cohen kappa (EditLens R vs Llama)        = {k_el:.3f}")
r_de = df[["score_editlens","score_desklib_academic"]].dropna().corr().iloc[0,1]
r_dl = df[["score_editlens_llama","score_desklib_academic"]].dropna().corr().iloc[0,1]
r_el = df[["score_editlens","score_editlens_llama"]].dropna().corr().iloc[0,1]
print(f"  Pearson r (desklib acad vs EditLens R)   = {r_de:.3f}")
print(f"  Pearson r (desklib acad vs EditLens L)   = {r_dl:.3f}")
print(f"  Pearson r (EditLens R vs Llama)          = {r_el:.3f}")

# Save consolidated
out = {
    "calibration_window": [CAL_LO, CAL_HI],
    "analytic_window": [ANALYTIC_LO, 2026],
    "n_analytic": int(len(df)),
    "n_calibration": int(len(cal)),
    "P95": {
        "EditLens_R_single":   P95_e,
        "EditLens_R_multi":    P95_emw,
        "EditLens_Llama":      P95_l,
        "desklib_academic":    P95_d,
    },
    "yearly": yearly.to_dict(orient="records"),
    "h1_step": h1,
    "cohen_kappa": {"desklib_acad_vs_editlens_r": float(k_de),
                    "desklib_acad_vs_editlens_l": float(k_dl),
                    "editlens_r_vs_l":            float(k_el)},
    "pearson_r_detectors": {"desklib_acad_vs_editlens_r": float(r_de),
                            "desklib_acad_vs_editlens_l": float(r_dl),
                            "editlens_r_vs_l":            float(r_el)},
}
(RES/"main_analysis_results.json").write_text(json.dumps(out, indent=2, default=str))
print(f"\nSaved -> {RES/'main_analysis_results.json'}")
