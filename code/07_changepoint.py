"""
Step 7 — Blinded changepoint detection on per-cycle outcomes.

  - Pettitt test (single change in mean / location)
  - Binary segmentation via ruptures (CART-style, model='l2')

Both are run with no year seeding, no hypothesis-conditioning.  Reported
result: detected change conference-year for each method on each outcome.
"""

import pandas as pd, numpy as np, json
from pathlib import Path
import ruptures as rpt
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parent.parent  # repo root
agg_full = pd.read_csv(ROOT / "results" / "yearly_aggregates.csv")
# Restrict changepoint search to 2009+ since 2008-2009 format break is a known
# non-LLM artifact already accounted for in calibration window.
agg = agg_full[agg_full["year"] >= 2009].reset_index(drop=True)
print(f"Searching for changepoints in {agg['year'].min()}-{agg['year'].max()} window (post-format-change era).")

def pettitt(y):
    """Non-parametric single change-point in location.
    Returns (k_index, K_stat, p_value)."""
    n = len(y)
    U = np.zeros(n)
    for t in range(n):
        s = 0.0
        for i in range(t+1):
            for j in range(t+1, n):
                s += np.sign(y[j] - y[i])
        U[t] = s
    Uabs = np.abs(U)
    K = Uabs.max()
    k = int(np.argmax(Uabs))
    # Approximate p-value (Pettitt 1979)
    p = 2.0 * np.exp(-6 * K**2 / (n**3 + n**2))
    return k, float(K), float(min(1.0, p))

def binseg(y):
    algo = rpt.Binseg(model="l2").fit(y.reshape(-1, 1))
    bkps = algo.predict(n_bkps=1)
    # ruptures returns the index AFTER the change
    return int(bkps[0] - 1)

out = {"intervention_pre_specified_conference_year": 2025,
       "search_window": [int(agg['year'].min()), int(agg['year'].max())]}
for col in ["mean_score", "pct_binary", "pct_ai_edited_or_ai"]:
    y = agg[col].values.astype(float)
    years = agg["year"].values
    k_pet, K_pet, p_pet = pettitt(y)
    k_bs = binseg(y)
    # Multi-break Binseg to give richer changepoint picture
    multi = {}
    for n in [1, 2, 3]:
        algo = rpt.Binseg(model="l2").fit(y.reshape(-1, 1))
        bkps = algo.predict(n_bkps=n)
        multi[f"n_bkps={n}"] = [int(years[k-1]) for k in bkps[:-1]]
    print(f"\n{col}:")
    print(f"  Pettitt:  k={k_pet} -> last conference year before break = {years[k_pet]} "
          f"(K={K_pet:.1f}, p~{p_pet:.4f})")
    print(f"  Binseg n=1:  break after {years[k_bs]}")
    print(f"  Binseg multi: {multi}")
    out[col] = {
        "pettitt_change_after_year": int(years[k_pet]),
        "pettitt_K": K_pet,
        "pettitt_p_approx": p_pet,
        "binseg_change_after_year_n1": int(years[k_bs]),
        "binseg_multi_breaks": multi,
    }

(ROOT / "results" / "changepoint_results.json").write_text(json.dumps(out, indent=2))
print(f"\nSaved -> {ROOT / 'results' / 'changepoint_results.json'}")
