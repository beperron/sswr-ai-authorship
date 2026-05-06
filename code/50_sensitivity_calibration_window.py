"""
Sensitivity check: calibration window 2010-2015 vs the pre-registered 2010-2017.

Motivation: Grammarly's freemium product launched May 2015. The April 2016
submission deadline (conf 2017) is the first SSWR cycle whose abstracts
could plausibly carry Grammarly polish. The pre-registered 2010-2017 window
therefore includes one cycle (conf 2017) of possible Grammarly-polished
abstracts. A 2010-2015 window excludes this cycle entirely.

This script recomputes the headline numbers under both windows and prints
a side-by-side comparison. P95 thresholds, yearly above-P95 proportions,
and the H1 segmented-regression step at conf 2025 are reported per detector.

Reads:
  data/scores_editlens_roberta.pkl
  data/scores_editlens_llama.pkl
  data/scores_primary_academic.pkl

Writes:
  results/sensitivity_calibration_2010_2015.json
"""

import pandas as pd, numpy as np, json
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
RES  = ROOT / "results"

edl_r = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta.pkl")[
    ["id","year","score_editlens"]]
edl_l = pd.read_pickle(ROOT/"data"/"scores_editlens_llama.pkl")[
    ["id","score_editlens_llama"]]
desk  = pd.read_pickle(ROOT/"data"/"scores_primary_academic.pkl")[
    ["id","score_primary"]].rename(columns={"score_primary":"score_desklib_academic"})

df = edl_r.merge(edl_l, on="id").merge(desk, on="id")
for c in ["score_editlens","score_editlens_llama","score_desklib_academic"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df[df.year >= 2010].copy()
print(f"Analytic N (conf 2010-2026) = {len(df):,}\n")

DETECTORS = [
    ("EditLens RoBERTa-large", "score_editlens"),
    ("EditLens Llama-3.2-3B",  "score_editlens_llama"),
    ("desklib academic",       "score_desklib_academic"),
]

WINDOWS = [
    ("preregistered_2010_2017", 2010, 2017),
    ("sensitivity_2010_2015",   2010, 2015),
]


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


results = {}
for tag, lo, hi in WINDOWS:
    cal = df[(df.year>=lo) & (df.year<=hi)]
    print(f"=== Calibration window {lo}-{hi} (n={len(cal):,}) ===")
    win_out = {"window": [lo, hi], "n_cal": int(len(cal)), "P95": {}, "yearly": {}, "h1_step": {}}

    # P95 thresholds
    for name, col in DETECTORS:
        p95 = float(np.quantile(cal[col], 0.95))
        win_out["P95"][name] = p95
        df[f"bin__{tag}__{col}"] = (df[col] >= p95).astype(int)
        print(f"  P95 {name:<26} = {p95:.4f}")

    # Yearly proportions
    yr_tab = df.groupby("year").size().rename("n").to_frame()
    for name, col in DETECTORS:
        yr_tab[name] = df.groupby("year")[f"bin__{tag}__{col}"].mean()*100
    win_out["yearly"] = yr_tab.reset_index().to_dict(orient="records")

    # H1 step
    print(f"\n  H1 ITS step at conf 2025:")
    for name, col in DETECTORS:
        ys = yr_tab[name].values / 100
        yrs = yr_tab.index.values
        step = its(yrs, ys)
        win_out["h1_step"][name] = step
        print(f"    {name:<26} = {step['level_pp']:+.1f} pp  CI95=[{step['ci95_lo_pp']:+.1f}, {step['ci95_hi_pp']:+.1f}]  p={step['p']:.4g}")

    # 2026 yearly
    y26 = yr_tab.loc[2026]
    print(f"\n  2026 above-P95 (n={int(y26['n']):,}):")
    for name, col in DETECTORS:
        print(f"    {name:<26} = {y26[name]:.1f}%")
    print()

    results[tag] = win_out

# ---- Side-by-side comparison ----
print("="*80)
print("Side-by-side: P95 thresholds")
print("="*80)
print(f"{'Detector':<26}  {'2010-2017':>12}  {'2010-2015':>12}  {'Δ':>10}")
for name, _ in DETECTORS:
    p17 = results["preregistered_2010_2017"]["P95"][name]
    p15 = results["sensitivity_2010_2015"]["P95"][name]
    print(f"{name:<26}  {p17:>12.4f}  {p15:>12.4f}  {p15-p17:>+10.4f}")

print("\n" + "="*80)
print("Side-by-side: H1 ITS step at conf 2025")
print("="*80)
print(f"{'Detector':<26}  {'2010-2017':>22}  {'2010-2015':>22}")
for name, _ in DETECTORS:
    s17 = results["preregistered_2010_2017"]["h1_step"][name]
    s15 = results["sensitivity_2010_2015"]["h1_step"][name]
    s17_str = f"{s17['level_pp']:+.1f} [{s17['ci95_lo_pp']:+.1f}, {s17['ci95_hi_pp']:+.1f}]"
    s15_str = f"{s15['level_pp']:+.1f} [{s15['ci95_lo_pp']:+.1f}, {s15['ci95_hi_pp']:+.1f}]"
    print(f"{name:<26}  {s17_str:>22}  {s15_str:>22}")

print("\n" + "="*80)
print("Side-by-side: yearly above-P95 % (per detector, %)")
print("="*80)
yr17 = pd.DataFrame(results["preregistered_2010_2017"]["yearly"]).set_index("year")
yr15 = pd.DataFrame(results["sensitivity_2010_2015"]["yearly"]).set_index("year")
for name, _ in DETECTORS:
    print(f"\n  {name}:")
    print(f"  {'year':>6}  {'2010-2017':>10}  {'2010-2015':>10}  {'Δ pp':>8}")
    for y in sorted(yr17.index):
        v17 = yr17.loc[y, name]
        v15 = yr15.loc[y, name]
        print(f"  {y:>6}  {v17:>10.1f}  {v15:>10.1f}  {v15-v17:>+8.1f}")

# Save JSON
(RES/"sensitivity_calibration_2010_2015.json").write_text(
    json.dumps(results, indent=2, default=str))
print(f"\nSaved -> {RES/'sensitivity_calibration_2010_2015.json'}")
