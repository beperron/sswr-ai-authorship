"""
Block-bootstrap confidence intervals for ITS step at intervention.

Per peer-review item 3, with only 22 yearly observations, parametric Newey-West
SEs are weak. Block bootstrap by resampling years with replacement gives a
distribution-free CI for the level change at the 2025 intervention.
"""

import pandas as pd, numpy as np, json
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
agg = pd.read_csv(ROOT / "results" / "yearly_aggregates.csv")
N_BOOT = 2000
RNG = np.random.default_rng(0)

def its_step(agg_df, outcome, intervention=2025):
    y = agg_df[outcome].values.astype(float)
    yrs = agg_df["year"].values.astype(float)
    T = yrs - intervention
    I = (yrs >= intervention).astype(float)
    X = np.column_stack([np.ones_like(T), T, I, T*I])
    try:
        mod = sm.OLS(y, pd.DataFrame(X, columns=["const","T","I","TxI"])).fit()
        return float(mod.params["I"])
    except Exception:
        return np.nan

results = {}
for outcome in ["mean_score","pct_binary","pct_ai_edited_or_ai"]:
    point = its_step(agg, outcome)
    boots = np.empty(N_BOOT, dtype=float)
    for b in range(N_BOOT):
        idx = RNG.integers(0, len(agg), size=len(agg))
        sub = agg.iloc[idx].copy()
        # need enough variation pre and post
        if (sub["year"]>=2025).sum() < 1 or (sub["year"]<2025).sum() < 3:
            boots[b] = np.nan
            continue
        boots[b] = its_step(sub, outcome)
    boots = boots[~np.isnan(boots)]
    lo, hi = np.quantile(boots, [0.005, 0.995])     # 99% percentile interval
    lo90, hi90 = np.quantile(boots, [0.05, 0.95])   # 90% interval
    results[outcome] = {
        "point": point,
        "boot_99CI": [float(lo), float(hi)],
        "boot_90CI": [float(lo90), float(hi90)],
        "n_boot": int(len(boots)),
    }
    print(f"{outcome}:  point={point:+.4f}, 99% boot CI [{lo:+.4f}, {hi:+.4f}], 90% [{lo90:+.4f}, {hi90:+.4f}]")

(ROOT / "results" / "bootstrap_its.json").write_text(json.dumps(results, indent=2))
print(f"Saved -> {ROOT/'results'/'bootstrap_its.json'}")
