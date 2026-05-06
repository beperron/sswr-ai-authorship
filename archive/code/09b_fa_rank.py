"""
First-author rank stratification.

Cohorts: assistant, associate, full, postdoc, doctoral (other = pooled control).
Per-year outcomes per cohort + DiD pre-vs-post mature LLM availability.
"""

import pandas as pd, numpy as np, json
from pathlib import Path
import statsmodels.api as sm

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
df = pd.read_pickle(ROOT / "data" / "scores_labeled.pkl")
df["score_primary"] = pd.to_numeric(df["score_primary"], errors="coerce")
df["label_binary"] = pd.to_numeric(df["label_binary"], errors="coerce")

# Merge fa_rank in (was added to corpus_preprocessed after scoring)
preproc = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl")
if "fa_rank" not in df.columns:
    df = df.merge(preproc[["id", "fa_rank", "fa_position_norm"]], on="id", how="left")
print(f"fa_rank distribution in labeled data: \n{df['fa_rank'].value_counts().to_string()}")

# Period: pre = 2005-2024, post = 2025-2026 (matches qual-vs-quant)
df["period"] = np.where(df["year"] >= 2025, "post", "pre")
RANKS = ["assistant", "associate", "full", "postdoc", "doctoral", "other"]

# Per-year per-rank table
agg = df.groupby(["year", "fa_rank"]).agg(
    n=("score_primary", "size"),
    mean_score=("score_primary", "mean"),
    pct_binary=("label_binary", "mean"),
    pct_ai_edited_or_ai=("label_ternary", lambda x: (x != "human").mean()),
).reset_index()
agg.to_csv(ROOT / "results" / "fa_rank_yearly.csv", index=False)
print("Per-year per-rank table written.")

# Pre vs post summary
print("\n=== Pre vs Post by first-author rank ===")
piv = df.groupby(["fa_rank", "period"])[["score_primary", "label_binary"]].mean().round(4)
print(piv.to_string())

# Pre/Post % AI by rank with deltas
summary = []
for r in RANKS:
    d = df[df["fa_rank"] == r]
    pre = d[d["period"] == "pre"]
    post = d[d["period"] == "post"]
    summary.append({
        "rank": r,
        "n_pre": len(pre), "n_post": len(post),
        "mean_pre": pre["score_primary"].mean(),
        "mean_post": post["score_primary"].mean(),
        "pct_binary_pre": pre["label_binary"].mean(),
        "pct_binary_post": post["label_binary"].mean(),
        "delta_mean": post["score_primary"].mean() - pre["score_primary"].mean(),
        "delta_pct_binary": post["label_binary"].mean() - pre["label_binary"].mean(),
    })
summ = pd.DataFrame(summary)
summ.to_csv(ROOT / "results" / "fa_rank_pre_post.csv", index=False)
print("\nPre-vs-post by rank:")
print(summ.round(4).to_string(index=False))

# DiD-style regression with rank-by-period interactions, reference = assistant
df_did = df[df["fa_rank"].isin(RANKS)].copy()
df_did["post"] = (df_did["period"] == "post").astype(int)
# dummies for rank, drop assistant as reference
for r in [x for x in RANKS if x != "assistant"]:
    df_did[f"r_{r}"] = (df_did["fa_rank"] == r).astype(int)
    df_did[f"r_{r}_post"] = df_did[f"r_{r}"] * df_did["post"]

cols = ["post"] + [f"r_{r}" for r in RANKS if r != "assistant"] + \
       [f"r_{r}_post" for r in RANKS if r != "assistant"]

out = {}
for outcome in ["score_primary", "label_binary"]:
    X = sm.add_constant(df_did[cols])
    mod = sm.OLS(df_did[outcome], X).fit(cov_type="HC3")
    print(f"\n--- DiD: {outcome} (reference rank = assistant) ---")
    print(mod.summary().tables[1])
    out[outcome] = {
        "params": mod.params.round(6).to_dict(),
        "pvalues": mod.pvalues.round(6).to_dict(),
        "interpretation": "Coefficients on r_<rank>_post are the differential post-period jump "
                          "for that rank vs. assistant professors.",
    }

(ROOT / "results" / "fa_rank_did.json").write_text(json.dumps(out, indent=2, default=str))
print(f"\nSaved -> {ROOT / 'results' / 'fa_rank_did.json'}")
