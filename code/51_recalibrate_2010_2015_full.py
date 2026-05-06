"""
Full recalibration to a 2010-2015 baseline (replaces the pre-registered
2010-2017 window). Motivation: Grammarly's freemium product launched
May 2015, and the April 2016 submission deadline (conf 2017) is the first
SSWR cycle whose abstracts could plausibly carry Grammarly polish. The
2010-2015 window therefore predates any plausible Grammarly contamination.

Computes and saves all numbers needed to update the manuscript:
  * P95 thresholds (EditLens R, EditLens Llama, desklib academic)
  * Yearly above-P95 proportions
  * H1 ITS step at conf 2025 (segmented regression, Newey-West HAC)
  * H2 academic-rank DiD (assistant prof = ref) with full descriptive cells
  * H3 methodology DiD (qual vs quant) with descriptive cells
  * H4 within-baseline drift (now within 2010-2015)
  * Country DiD (US = ref) with cells
  * Prior-submissions cohort DiD (Gartenberg-aligned) with cells
  * Cohen's kappa across detector pairs
  * Pearson r across detector pairs
  * Writing-quality FRE SD baseline (for Figure 2 standardization)

Writes:
  results/main_analysis_results.json                       (overwrites)
  results/h2_rank_h3_qual_did_2010_2015_calibration.json  (new)
  results/country_did_2010_2015_calibration.json          (new)
  results/h4_within_baseline_drift_2010_2015.json         (new)
  results/prior_submissions_analysis.json                  (overwrites)
  results/fre_baseline_2010_2015.json                      (new — for figures)
"""

import pandas as pd, numpy as np, json
import statsmodels.api as sm
from pathlib import Path
from sklearn.metrics import cohen_kappa_score

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
RES  = ROOT / "results"

CAL_LO, CAL_HI = 2010, 2015
ANALYTIC_LO    = 2010

print(f"Calibration window: {CAL_LO}-{CAL_HI}")
print(f"Analytic window: {ANALYTIC_LO}-2026")
print()

# ---- Load ----
edl_r = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta.pkl")[
    ["id","year","methodology","text_wc","score_editlens","bucket_editlens"]]
edl_l = pd.read_pickle(ROOT/"data"/"scores_editlens_llama.pkl")[
    ["id","score_editlens_llama","bucket_editlens_llama"]]
desk  = pd.read_pickle(ROOT/"data"/"scores_primary_academic.pkl")[
    ["id","score_primary"]].rename(columns={"score_primary":"score_desklib_academic"})
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
print(f"Analytic N = {len(df):,}")

# ---- P95 thresholds on 2010-2015 ----
cal = df[(df.year>=CAL_LO)&(df.year<=CAL_HI)]
P95_e   = float(np.quantile(cal.score_editlens,           0.95))
P95_l   = float(np.quantile(cal.score_editlens_llama,     0.95))
P95_d   = float(np.quantile(cal.score_desklib_academic,   0.95))
P95_emw = float(np.quantile(cal.score_editlens_mw,        0.95))
print(f"Calibration N = {len(cal):,}")
print(f"  P95 EditLens RoBERTa-large (single)       = {P95_e:.4f}")
print(f"  P95 EditLens RoBERTa-large (multi-window) = {P95_emw:.4f}")
print(f"  P95 EditLens Llama-3.2-3B                 = {P95_l:.4f}")
print(f"  P95 desklib academic                      = {P95_d:.4f}")

df["bin_e"] = (df.score_editlens         >= P95_e).astype(int)
df["bin_l"] = (df.score_editlens_llama   >= P95_l).astype(int)
df["bin_d"] = (df.score_desklib_academic >= P95_d).astype(int)

# ---- Yearly proportions ----
yearly = df.groupby("year").agg(
    n=("id","count"),
    pct_e=("bin_e", lambda x: round(x.mean()*100, 1)),
    pct_l=("bin_l", lambda x: round(x.mean()*100, 1)),
    pct_d=("bin_d", lambda x: round(x.mean()*100, 1)),
).reset_index()
print("\nYearly above-P95:")
print(yearly.to_string(index=False))

# ---- H1 ITS step ----
def its(yr, y, intervention=2025):
    yr = np.asarray(yr, dtype=float); y = np.asarray(y, dtype=float)
    T = yr - intervention
    I = (yr >= intervention).astype(float)
    X = sm.add_constant(pd.DataFrame({"T":T, "I":I, "TxI":T*I}))
    mod = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags":2})
    ci = mod.conf_int(0.05).loc["I"]
    return {
        "level_pp":   float(mod.params["I"])*100,
        "ci95_lo_pp": float(ci.iloc[0])*100,
        "ci95_hi_pp": float(ci.iloc[1])*100,
        "p":          float(mod.pvalues["I"]),
    }

print("\nH1 ITS step at conf 2025:")
h1 = {}
yr = yearly.year.values
for col, label in [("pct_e","EditLens RoBERTa-large"),
                   ("pct_l","EditLens Llama-3.2-3B"),
                   ("pct_d","desklib academic")]:
    r = its(yr, yearly[col].values/100)
    print(f"  {label:<26} = {r['level_pp']:+.1f} pp  CI95=[{r['ci95_lo_pp']:+.1f}, {r['ci95_hi_pp']:+.1f}]  p={r['p']:.4g}")
    h1[label] = r

# ---- Inter-detector convergence ----
k_de = float(cohen_kappa_score(df.bin_d, df.bin_e))
k_dl = float(cohen_kappa_score(df.bin_d, df.bin_l))
k_el = float(cohen_kappa_score(df.bin_e, df.bin_l))
r_de = float(df[["score_editlens","score_desklib_academic"]].dropna().corr().iloc[0,1])
r_dl = float(df[["score_editlens_llama","score_desklib_academic"]].dropna().corr().iloc[0,1])
r_el = float(df[["score_editlens","score_editlens_llama"]].dropna().corr().iloc[0,1])
print(f"\nKappa: desklib×R = {k_de:.3f}  desklib×L = {k_dl:.3f}  R×L = {k_el:.3f}")
print(f"Pearson r: desklib×R = {r_de:.3f}  desklib×L = {r_dl:.3f}  R×L = {r_el:.3f}")

# ---- Save main_analysis_results.json ----
out = {
    "calibration_window": [CAL_LO, CAL_HI],
    "analytic_window": [ANALYTIC_LO, 2026],
    "n_analytic": int(len(df)),
    "n_calibration": int(len(cal)),
    "P95": {"EditLens_R_single": P95_e, "EditLens_R_multi": P95_emw,
            "EditLens_Llama": P95_l, "desklib_academic": P95_d},
    "yearly": yearly.to_dict(orient="records"),
    "h1_step": h1,
    "cohen_kappa": {"desklib_acad_vs_editlens_r": k_de,
                    "desklib_acad_vs_editlens_l": k_dl,
                    "editlens_r_vs_l":            k_el},
    "pearson_r_detectors": {"desklib_acad_vs_editlens_r": r_de,
                            "desklib_acad_vs_editlens_l": r_dl,
                            "editlens_r_vs_l":            r_el},
}
(RES/"main_analysis_results.json").write_text(json.dumps(out, indent=2, default=str))

# ---- Three-period DiD (H2, H3, country, prior-subs) ----
NO_EXP  = (df.year>=ANALYTIC_LO) & (df.year<=2023)
PARTIAL = (df.year==2024)
FULL    = (df.year>=2025) & (df.year<=2026)

# Helper: rate cells per group × period × detector
def cells(group_col, group_value, det_col):
    out = {}
    for period_name, mask in [("no_exposure", NO_EXP), ("partial", PARTIAL), ("full", FULL)]:
        sub = df[mask & (df[group_col] == group_value)]
        if len(sub):
            out[period_name] = {"n": int(len(sub)),
                                "pct_above_P95": round(sub[det_col].mean()*100, 2)}
        else:
            out[period_name] = {"n": 0, "pct_above_P95": None}
    return out

# H2: academic rank
print("\n" + "="*70 + "\nH2 academic rank")
RANKS_TO_LABEL = {"postdoc":"postdoc","full":"full",
                  "associate":"associate","assistant":"assistant","doctoral":"doctoral"}
df["rank_label"] = df.fa_rank.map(RANKS_TO_LABEL)

h2_cells = {"EditLens_RoBERTa_large": {}, "desklib_academic": {}, "EditLens_Llama_3_2_3B": {}}
for r_label in ["doctoral","postdoc","assistant","associate","full"]:
    h2_cells["EditLens_RoBERTa_large"][r_label] = cells("rank_label", r_label, "bin_e")
    h2_cells["desklib_academic"][r_label]       = cells("rank_label", r_label, "bin_d")
    h2_cells["EditLens_Llama_3_2_3B"][r_label]  = cells("rank_label", r_label, "bin_l")

# DiD (no-exp vs full; drop partial). Categories: doctoral, assistant (ref).
h2_did = {}
for det_col, det_name, label in [("bin_e","EditLens_RoBERTa_large","EditLens R"),
                                  ("bin_d","desklib_academic","desklib academic"),
                                  ("bin_l","EditLens_Llama_3_2_3B","EditLens Llama")]:
    sub = df[df.rank_label.isin(["doctoral","assistant"]) & (NO_EXP | FULL)].copy()
    sub["post"] = FULL.loc[sub.index].astype(int)
    sub["doc"]  = (sub.rank_label=="doctoral").astype(int)
    sub["doc_post"] = sub.doc * sub.post
    X = sm.add_constant(sub[["post","doc","doc_post"]])
    mod = sm.OLS(sub[det_col], X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
    ci = mod.conf_int(0.05).loc["doc_post"]
    h2_did[det_name] = {
        "doctoral_x_full_pp": float(mod.params["doc_post"]*100),
        "ci95_lo_pp": float(ci.iloc[0]*100),
        "ci95_hi_pp": float(ci.iloc[1]*100),
        "p": float(mod.pvalues["doc_post"]),
    }
    print(f"  {label:<22}: doctoral × Full = {mod.params['doc_post']*100:+.2f} pp  CI95=[{ci.iloc[0]*100:+.2f}, {ci.iloc[1]*100:+.2f}]  p={mod.pvalues['doc_post']:.4g}")

# H3: methodology
print("\nH3 methodology")
h3_cells = {"EditLens_RoBERTa_large": {}, "desklib_academic": {}, "EditLens_Llama_3_2_3B": {}}
for m in ["qualitative","quantitative"]:
    h3_cells["EditLens_RoBERTa_large"][m] = cells("methodology", m, "bin_e")
    h3_cells["desklib_academic"][m]       = cells("methodology", m, "bin_d")
    h3_cells["EditLens_Llama_3_2_3B"][m]  = cells("methodology", m, "bin_l")

h3_did = {}
for det_col, det_name, label in [("bin_e","EditLens_RoBERTa_large","EditLens R"),
                                  ("bin_d","desklib_academic","desklib academic"),
                                  ("bin_l","EditLens_Llama_3_2_3B","EditLens Llama")]:
    sub = df[df.methodology.isin(["qualitative","quantitative"]) & (NO_EXP | FULL)].copy()
    sub["post"] = FULL.loc[sub.index].astype(int)
    sub["qual"] = (sub.methodology=="qualitative").astype(int)
    sub["qual_post"] = sub.qual * sub.post
    X = sm.add_constant(sub[["post","qual","qual_post"]])
    mod = sm.OLS(sub[det_col], X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
    ci = mod.conf_int(0.05).loc["qual_post"]
    h3_did[det_name] = {
        "qualitative_x_full_pp": float(mod.params["qual_post"]*100),
        "ci95_lo_pp": float(ci.iloc[0]*100),
        "ci95_hi_pp": float(ci.iloc[1]*100),
        "p": float(mod.pvalues["qual_post"]),
    }
    print(f"  {label:<22}: qualitative × Full = {mod.params['qual_post']*100:+.2f} pp  CI95=[{ci.iloc[0]*100:+.2f}, {ci.iloc[1]*100:+.2f}]  p={mod.pvalues['qual_post']:.4g}")

# Save H2/H3 JSON
h2h3 = {
    "spec": "DiD on no-exposure (conf 2010-2023) vs full-exposure (conf 2025-2026); partial 2024 dropped; year-clustered SEs. P95 thresholds calibrated on conf 2010-2015.",
    "calibration_window": "2010-2015",
    "P95_thresholds": {"EditLens_R": P95_e, "EditLens_Llama": P95_l, "desklib_acad": P95_d},
    "h2_rank": {"reference_category": "assistant_professor",
                "cells": h2_cells, "did_full_vs_no_exposure": h2_did},
    "h3_methodology": {"reference_category": "quantitative",
                       "cells": h3_cells, "did_full_vs_no_exposure": h3_did},
}
(RES/"h2_rank_h3_qual_did_2010_2015_calibration.json").write_text(json.dumps(h2h3, indent=2, default=str))

# Country DiD
print("\nCountry DiD (US = ref)")
country_cells = {"EditLens_RoBERTa_large": {}, "desklib_academic": {}, "EditLens_Llama_3_2_3B": {}}
cdf = df[df.fa_cohort.notna()].copy()
for k in ["US","Other Anglophone","Non-Anglophone"]:
    sub_us = cdf[cdf.fa_cohort==k]
    key = {"US":"US","Other Anglophone":"Other_Anglophone","Non-Anglophone":"Non_Anglophone"}[k]
    for det_col, det_name in [("bin_e","EditLens_RoBERTa_large"),
                              ("bin_d","desklib_academic"),
                              ("bin_l","EditLens_Llama_3_2_3B")]:
        country_cells[det_name][key] = {}
        for period_name, mask in [("no_exposure", NO_EXP), ("partial", PARTIAL), ("full", FULL)]:
            sub = cdf[mask.loc[cdf.index] & (cdf.fa_cohort == k)]
            if len(sub):
                country_cells[det_name][key][period_name] = {"n": int(len(sub)),
                                                             "pct_above_P95": round(sub[det_col].mean()*100, 2)}
            else:
                country_cells[det_name][key][period_name] = {"n": 0, "pct_above_P95": None}

country_did = {}
for det_col, det_name in [("bin_e","EditLens_RoBERTa_large"),
                          ("bin_d","desklib_academic"),
                          ("bin_l","EditLens_Llama_3_2_3B")]:
    sub = cdf[NO_EXP.loc[cdf.index] | FULL.loc[cdf.index]].copy()
    sub["post"]      = FULL.loc[sub.index].astype(int)
    sub["other_ang"] = (sub.fa_cohort=="Other Anglophone").astype(int)
    sub["non_ang"]   = (sub.fa_cohort=="Non-Anglophone").astype(int)
    sub["other_ang_post"] = sub.other_ang * sub.post
    sub["non_ang_post"]   = sub.non_ang   * sub.post
    X = sm.add_constant(sub[["post","other_ang","non_ang","other_ang_post","non_ang_post"]])
    mod = sm.OLS(sub[det_col], X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
    co = mod.conf_int(0.05)
    country_did[det_name] = {
        "other_anglophone_x_full_pp": float(mod.params["other_ang_post"]*100),
        "other_ang_ci95_lo_pp": float(co.loc["other_ang_post",0]*100),
        "other_ang_ci95_hi_pp": float(co.loc["other_ang_post",1]*100),
        "other_ang_p": float(mod.pvalues["other_ang_post"]),
        "non_anglophone_x_full_pp": float(mod.params["non_ang_post"]*100),
        "non_ang_ci95_lo_pp": float(co.loc["non_ang_post",0]*100),
        "non_ang_ci95_hi_pp": float(co.loc["non_ang_post",1]*100),
        "non_ang_p": float(mod.pvalues["non_ang_post"]),
    }
    print(f"  {det_name}: OtherAng×Full = {mod.params['other_ang_post']*100:+.2f} pp  NonAng×Full = {mod.params['non_ang_post']*100:+.2f} pp")

(RES/"country_did_2010_2015_calibration.json").write_text(json.dumps({
    "spec": "DiD on no-exposure (conf 2010-2023) vs full-exposure (conf 2025-2026); partial 2024 dropped; year-clustered SEs; US = reference; P95 thresholds calibrated on conf 2010-2015.",
    "calibration_window": "2010-2015",
    "P95_thresholds": {"EditLens_R": P95_e, "EditLens_Llama": P95_l, "desklib_acad": P95_d},
    "reference_category": "US",
    "cells": country_cells,
    "did_full_vs_no_exposure": country_did,
}, indent=2, default=str))

# H4 within-baseline drift on 2010-2015
print("\nH4 within-baseline drift 2010-2015")
cal2 = df[(df.year>=CAL_LO)&(df.year<=CAL_HI)].copy()
cal2["log_wc"] = np.log(cal2.text_wc.astype(float).clip(lower=1))
cal2["year_centered"] = cal2.year - cal2.year.mean()
h4 = {"calibration_window": f"{CAL_LO}-{CAL_HI}",
      "spec": "abstract-level OLS of detector score on year (centered) and log(text_wc), year-clustered SEs"}
for col, key, label in [("score_editlens","EditLens_RoBERTa_large","EditLens R"),
                         ("score_desklib_academic","desklib_academic","desklib academic")]:
    X = sm.add_constant(cal2[["year_centered","log_wc"]])
    mod = sm.OLS(cal2[col], X).fit(cov_type="cluster", cov_kwds={"groups": cal2.year.values})
    h4[key] = {"n": int(len(cal2)),
               "beta_year": float(mod.params["year_centered"]),
               "se_year":   float(mod.bse["year_centered"]),
               "p_year":    float(mod.pvalues["year_centered"]),
               "beta_log_wc": float(mod.params["log_wc"]),
               "mean_score_lo": float(cal2.loc[cal2.year==CAL_LO, col].mean()),
               "mean_score_hi": float(cal2.loc[cal2.year==CAL_HI, col].mean())}
    print(f"  {label}: β = {mod.params['year_centered']:+.6f}  p = {mod.pvalues['year_centered']:.4g}")
(RES/"h4_within_baseline_drift_2010_2015.json").write_text(json.dumps(h4, indent=2, default=str))

# Prior-submissions cohort
print("\nPrior-submissions cohort")
auth_full = pd.read_csv(ROOT/"data"/"sswr_paper_authors.csv",
                        dtype=str, keep_default_na=False)
papers_year = pd.read_csv(ROOT/"data"/"sswr_papers.csv",
                          usecols=["id","year"])
papers_year.columns = ["paper_id","year"]
papers_year["paper_id"] = papers_year["paper_id"].astype(str)
firsts_all = auth_full[auth_full.author_order=="1"].copy()
firsts_all = firsts_all.merge(papers_year, on="paper_id", how="left")
firsts_all["year"] = pd.to_numeric(firsts_all.year, errors="coerce")
firsts_all = firsts_all.dropna(subset=["year"])
firsts_all["year"] = firsts_all["year"].astype(int)

prior_count = {}
for canon, group in firsts_all.groupby("canonical_author_id"):
    years_sorted = sorted(group.year.tolist())
    seen = 0
    for paper_id, py in zip(group.paper_id, group.year):
        prior_count[paper_id] = sum(1 for y in years_sorted if y < py)

df["prior_n"] = df.id.map(prior_count)
def bucket(n):
    if pd.isna(n): return None
    if n == 0: return "new"
    if n <= 2: return "early"
    return "established"
df["prior_bucket"] = df.prior_n.map(bucket)

# Rates by bucket × period
ps_rates = {}
for det_col, det_name in [("bin_e","EditLens RoBERTa-large"),
                          ("bin_l","EditLens Llama-3.2-3B"),
                          ("bin_d","desklib academic")]:
    rows = []
    for b in ["new","early","established"]:
        for period_name, mask in [("no_exposure", NO_EXP), ("partial", PARTIAL), ("full", FULL)]:
            sub = df[mask & (df.prior_bucket == b)]
            if len(sub):
                rows.append({"bucket": b, "exposure": period_name,
                             "n": int(len(sub)),
                             "pct": round(sub[det_col].mean()*100, 2)})
    ps_rates[det_name] = rows

# DiD: new vs established (ref), no-exp vs full
ps_did = {}
for det_col, det_name in [("bin_e","EditLens_RoBERTa_large"),
                           ("bin_l","EditLens_Llama_3_2_3B"),
                           ("bin_d","desklib_academic")]:
    sub = df[df.prior_bucket.isin(["new","established"]) & (NO_EXP | FULL)].copy()
    sub["post"] = FULL.loc[sub.index].astype(int)
    sub["new"] = (sub.prior_bucket=="new").astype(int)
    sub["new_post"] = sub.new * sub.post
    X = sm.add_constant(sub[["post","new","new_post"]])
    mod = sm.OLS(sub[det_col], X).fit(cov_type="cluster", cov_kwds={"groups": sub.year.values})
    ci = mod.conf_int(0.05).loc["new_post"]
    ps_did[det_name] = {
        "new_x_full_pp": float(mod.params["new_post"]*100),
        "ci95_lo_pp": float(ci.iloc[0]*100),
        "ci95_hi_pp": float(ci.iloc[1]*100),
        "p": float(mod.pvalues["new_post"]),
    }
    print(f"  {det_name}: new × Full = {mod.params['new_post']*100:+.2f} pp  CI95=[{ci.iloc[0]*100:+.2f}, {ci.iloc[1]*100:+.2f}]  p={mod.pvalues['new_post']:.4g}")

(RES/"prior_submissions_analysis.json").write_text(json.dumps({
    "method_note": "For each abstract, the first author's canonical_author_id was looked up in the harmonized SSWR History Database, and prior_n was computed as the count of earlier (year < current_year) submissions by that canonical author across the full archive. Buckets: new=0 prior, early=1-2 prior, established=3+ prior. Analytic window: conf 2010-2026. P95 thresholds calibrated on conf 2010-2015.",
    "calibration_window": "2010-2015",
    "n_total": int(df.prior_bucket.notna().sum()),
    "P95": {"EditLens_R": P95_e, "EditLens_Llama": P95_l, "desklib_acad": P95_d},
    "rates_by_bucket_period": ps_rates,
    "did_new_vs_established": ps_did,
}, indent=2, default=str))

# ---- Writing-quality FRE SD baseline (used in Figure 2) ----
# Figure 2 uses the Hassan/Gartenberg-code FRE (scores_hassan.pkl), NOT the
# textstat reimplementation that lives in writing_quality.pkl. The baseline
# mean and SD differ between the two.
print("\nWriting-quality FRE baseline")
hassan = pd.read_pickle(ROOT/"data"/"scores_hassan.pkl")[["id","hassan_fre"]]
hassan["hassan_fre"] = pd.to_numeric(hassan["hassan_fre"], errors="coerce")
df_hassan = df[["id","year"]].merge(hassan, on="id")
fre_h = df_hassan.loc[df_hassan.year.between(CAL_LO, CAL_HI), "hassan_fre"].dropna()
fre_h_mean = float(fre_h.mean()); fre_h_sd = float(fre_h.std())
fre_t = df.loc[df.year.between(CAL_LO, CAL_HI), "flesch_reading_ease"].dropna()
fre_t_mean = float(fre_t.mean()); fre_t_sd = float(fre_t.std())
print(f"  Hassan FRE 2010-2015 baseline: mean = {fre_h_mean:.3f}, SD = {fre_h_sd:.3f}, n = {len(fre_h):,}")
print(f"  Textstat FRE 2010-2015 baseline: mean = {fre_t_mean:.3f}, SD = {fre_t_sd:.3f}, n = {len(fre_t):,}")
(RES/"fre_baseline_2010_2015.json").write_text(json.dumps({
    "calibration_window": [CAL_LO, CAL_HI],
    "hassan_n": int(len(fre_h)),
    "hassan_fre_mean": fre_h_mean,
    "hassan_fre_sd":   fre_h_sd,
    "textstat_n": int(len(fre_t)),
    "textstat_fre_mean": fre_t_mean,
    "textstat_fre_sd":   fre_t_sd,
}, indent=2))

print("\nDONE.")
