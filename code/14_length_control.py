"""
Length-controlled abstract-level regression.

Tests whether the post-period (2025+) step survives controlling for
abstract word count, since RAID detectors are known to be length-sensitive.

Three outcomes (continuous score, binary AI label, AI-edited+AI label) are
each regressed on:
  - post indicator
  - log(word count)
  - their interaction
with year-clustered SEs.

Also: per-year mean score adjusted for word-count distribution shift.
"""

import pandas as pd, numpy as np, json
import statsmodels.api as sm
from pathlib import Path

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
df = pd.read_pickle(ROOT / "data" / "scores_labeled.pkl")
df["score_primary"] = pd.to_numeric(df["score_primary"], errors="coerce")
df["label_binary"]  = pd.to_numeric(df["label_binary"], errors="coerce")
df["label_ternary_pos"] = (df["label_ternary"] != "human").astype(int)
df["post"] = (df["year"] >= 2025).astype(int)
df["log_wc"] = np.log(df["text_wc"].astype(float).clip(lower=1))
df["log_wc_c"] = df["log_wc"] - df["log_wc"].mean()

# Word-count drift over time
print("Word-count by era:")
print(df.groupby(np.where(df.year>=2025,"post","pre"))["text_wc"].describe().round(1).to_string())

results = {}
for outcome, lab in [("score_primary","mean_score"),
                     ("label_binary","pct_binary"),
                     ("label_ternary_pos","pct_AI_edited_or_AI")]:
    print(f"\n=== {lab} ===")
    # Without length control
    X1 = sm.add_constant(df[["post"]])
    m1 = sm.OLS(df[outcome], X1).fit(cov_type="cluster",
                                     cov_kwds={"groups": df["year"].values})
    # With length control (additive)
    X2 = sm.add_constant(df[["post","log_wc_c"]])
    m2 = sm.OLS(df[outcome], X2).fit(cov_type="cluster",
                                     cov_kwds={"groups": df["year"].values})
    # With length control + interaction
    df["post_logwc"] = df["post"] * df["log_wc_c"]
    X3 = sm.add_constant(df[["post","log_wc_c","post_logwc"]])
    m3 = sm.OLS(df[outcome], X3).fit(cov_type="cluster",
                                     cov_kwds={"groups": df["year"].values})

    r = {
        "no_length_control": {
            "post_beta": float(m1.params["post"]),
            "post_se":   float(m1.bse["post"]),
            "post_p":    float(m1.pvalues["post"])},
        "with_length_additive": {
            "post_beta": float(m2.params["post"]),
            "post_se":   float(m2.bse["post"]),
            "post_p":    float(m2.pvalues["post"]),
            "log_wc_beta": float(m2.params["log_wc_c"]),
            "log_wc_p":    float(m2.pvalues["log_wc_c"])},
        "with_length_interaction": {
            "post_beta": float(m3.params["post"]),
            "post_se":   float(m3.bse["post"]),
            "post_p":    float(m3.pvalues["post"]),
            "interaction_beta": float(m3.params["post_logwc"]),
            "interaction_p":    float(m3.pvalues["post_logwc"])},
    }
    print(f"  Post β  : no-control = {r['no_length_control']['post_beta']:+.4f} (p={r['no_length_control']['post_p']:.4f})")
    print(f"            additive   = {r['with_length_additive']['post_beta']:+.4f} (p={r['with_length_additive']['post_p']:.4f})")
    print(f"            w/inter    = {r['with_length_interaction']['post_beta']:+.4f} (p={r['with_length_interaction']['post_p']:.4f})")
    print(f"  log_wc additive β = {r['with_length_additive']['log_wc_beta']:+.4f} (p={r['with_length_additive']['log_wc_p']:.4f})")
    results[lab] = r

(ROOT / "results" / "length_control.json").write_text(json.dumps(results, indent=2, default=str))
print(f"\nSaved -> results/length_control.json")
