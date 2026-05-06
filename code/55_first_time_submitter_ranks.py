"""
Rank distribution of first-time SSWR submitters.

For each paper in the analytic corpus (conf 2010-2026, N = 21,569), look up
the first author's academic rank and prior-submission count. Then describe
the rank distribution among first-time submitters (prior_n = 0, the "New"
bucket in the H2 prior-submissions analysis).

Question being asked: are "New" first authors predominantly early-career
investigators (doctoral students, postdocs, assistant professors), or do
established faculty also debut at SSWR as first authors?

Outputs:
  - Console table of rank x exposure period for first-time submitters
  - Comparison: rank distribution for new vs early-career vs established
  - Per-cycle counts of new doctoral students etc., to test stability over time
  - results/first_time_submitter_ranks.json
"""

import pandas as pd, numpy as np, json
from pathlib import Path
from collections import defaultdict

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
RES  = ROOT / "results"

# ---- Load detector-scored corpus (same as main analysis) ----
edl_r = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta.pkl")[["id","year"]]
edl_r["id"] = edl_r["id"].astype(str)
edl_r = edl_r[edl_r.year >= 2010].copy()
analytic_ids = set(edl_r.id.tolist())
print(f"Analytic corpus: {len(edl_r):,} abstracts (conf 2010-2026)")

# ---- Load preprocessed corpus to get fa_rank ----
preproc = pd.read_pickle(ROOT/"data"/"corpus_preprocessed.pkl")[["id","fa_rank"]]
preproc["id"] = preproc["id"].astype(str)
df = edl_r.merge(preproc, on="id", how="left")

# ---- Compute prior_n via the all-author dedup method (same as Method G) ----
auth = pd.read_csv(ROOT/"data"/"sswr_paper_authors.csv",
                   dtype=str, keep_default_na=False)
papers = pd.read_csv(ROOT/"data"/"sswr_papers.csv", usecols=["id","year"])
papers.columns = ["paper_id","year"]
papers["paper_id"] = papers["paper_id"].astype(str)
auth = auth.merge(papers, on="paper_id", how="left")
auth["year"] = pd.to_numeric(auth.year, errors="coerce")
auth = auth.dropna(subset=["year"])
auth["year"] = auth["year"].astype(int)

auth_dedupe = auth.drop_duplicates(["canonical_author_id","paper_id"])
firsts_only = auth[auth.author_order=="1"].drop_duplicates("paper_id").copy()
yrs = auth_dedupe.groupby("canonical_author_id").year.apply(list).to_dict()

prior_count = {}
for paper_id, canon, py in zip(firsts_only.paper_id,
                                firsts_only.canonical_author_id,
                                firsts_only.year):
    yl = yrs.get(canon, [])
    prior_count[paper_id] = sum(1 for y in yl if y < py)

df["prior_n"] = df.id.map(prior_count)
def bucket(n):
    if pd.isna(n): return None
    if n == 0: return "new"
    if n <= 2: return "early"
    return "established"
df["prior_bucket"] = df.prior_n.map(bucket)

# Restrict to abstracts with usable rank info
df = df.dropna(subset=["fa_rank"]).copy()
print(f"Abstracts with non-null fa_rank: {len(df):,}")

# ---- Rank labels (canonical) ----
RANKS = ["doctoral","postdoc","assistant","associate","full","other"]
RANK_LABEL = {
    "doctoral":"Doctoral student",
    "postdoc":"Postdoc",
    "assistant":"Assistant professor",
    "associate":"Associate professor",
    "full":"Full professor",
    "other":"Other / unclassified",
}
df["rank_label"] = df.fa_rank.map(lambda r: RANK_LABEL.get(r, "Other / unclassified"))

# ---- Rank distribution among first-time submitters (overall) ----
new = df[df.prior_bucket == "new"]
print("\n" + "="*70)
print(f"RANK DISTRIBUTION AMONG FIRST-TIME SUBMITTERS (n = {len(new):,})")
print("="*70)
rank_counts = new.rank_label.value_counts()
rank_pct    = (rank_counts / len(new) * 100).round(1)
for rk, n in rank_counts.items():
    print(f"  {rk:<24} n = {n:>5,}   ({rank_pct[rk]:>4.1f}%)")

early_career = ["Doctoral student","Postdoc","Assistant professor"]
mid_career   = ["Associate professor"]
senior       = ["Full professor"]

ec_n  = sum(rank_counts.get(r, 0) for r in early_career)
mc_n  = sum(rank_counts.get(r, 0) for r in mid_career)
sr_n  = sum(rank_counts.get(r, 0) for r in senior)
oth_n = rank_counts.get("Other / unclassified", 0)
known_total = ec_n + mc_n + sr_n
print(f"\n  Of first-timers with classified rank (n = {known_total:,}):")
print(f"    Early career (doctoral/postdoc/assistant): {ec_n:,} ({ec_n/known_total*100:.1f}%)")
print(f"    Mid-career   (associate):                  {mc_n:,} ({mc_n/known_total*100:.1f}%)")
print(f"    Senior       (full):                       {sr_n:,} ({sr_n/known_total*100:.1f}%)")
print(f"    Other / unclassified (excluded):           {oth_n:,}")

# ---- Compare rank distribution across the three submission-experience buckets ----
print("\n" + "="*70)
print("RANK DISTRIBUTION BY SUBMISSION-EXPERIENCE BUCKET")
print("="*70)
print(f"{'Rank':<24}  {'New (0)':>14}  {'Early (1-2)':>14}  {'Established (3+)':>18}")
print("-" * 76)
for r in [RANK_LABEL[k] for k in RANKS]:
    new_pct  = (df[(df.prior_bucket=="new")&(df.rank_label==r)].shape[0] /
                max(1, df[df.prior_bucket=="new"].shape[0])) * 100
    early_pct = (df[(df.prior_bucket=="early")&(df.rank_label==r)].shape[0] /
                max(1, df[df.prior_bucket=="early"].shape[0])) * 100
    estab_pct = (df[(df.prior_bucket=="established")&(df.rank_label==r)].shape[0] /
                max(1, df[df.prior_bucket=="established"].shape[0])) * 100
    print(f"  {r:<22}  {new_pct:>5.1f}%        {early_pct:>5.1f}%         {estab_pct:>5.1f}%")

# ---- Stability of the rank composition of first-timers across exposure periods ----
NO_EXP  = (df.year>=2010) & (df.year<=2023)
PARTIAL = (df.year==2024)
FULL    = (df.year>=2025) & (df.year<=2026)

print("\n" + "="*70)
print("RANK COMPOSITION OF FIRST-TIMERS BY EXPOSURE PERIOD")
print("="*70)
print(f"{'Rank':<24}  {'No-exp':>10}  {'Partial':>10}  {'Full':>10}")
print("-"*60)
period_results = {}
for period_name, mask in [("no_exposure", NO_EXP), ("partial", PARTIAL), ("full", FULL)]:
    sub = df[mask & (df.prior_bucket=="new")]
    period_results[period_name] = {"n_total": int(len(sub)), "by_rank": {}}
    for r_key in RANKS:
        r_label = RANK_LABEL[r_key]
        n = int((sub.rank_label==r_label).sum())
        pct = round(n / max(1, len(sub)) * 100, 1)
        period_results[period_name]["by_rank"][r_key] = {"n": n, "pct": pct}

# Print table
for r_key in RANKS:
    r_label = RANK_LABEL[r_key]
    cells = []
    for period in ("no_exposure","partial","full"):
        d_ = period_results[period]["by_rank"][r_key]
        cells.append(f'{d_["pct"]:>5.1f}% ({d_["n"]:,})')
    print(f"  {r_label:<22}  " + "  ".join(f"{c:>10}" for c in cells))

print(f"\n  Totals: no_exp = {period_results['no_exposure']['n_total']:,}; "
      f"partial = {period_results['partial']['n_total']:,}; "
      f"full = {period_results['full']['n_total']:,}")

# ---- Detector signal among first-timers, broken down by rank ----
# Apply the 2010-2015 P95 thresholds we already have
P95 = json.loads((RES/"main_analysis_results.json").read_text())["P95"]
print("\n" + "="*70)
print("EDITLENS R ABOVE-P95 RATE: FIRST-TIMERS BY RANK x EXPOSURE")
print("="*70)
edl_r_full = pd.read_pickle(ROOT/"data"/"scores_editlens_roberta.pkl")[["id","score_editlens"]]
edl_r_full["id"] = edl_r_full["id"].astype(str)
df_full = df.merge(edl_r_full, on="id")
df_full["bin_e"] = (df_full.score_editlens >= P95["EditLens_R_single"]).astype(int)

rank_x_exposure = {}
print(f"{'Rank':<24}  {'No-exp %':>10}  {'Partial %':>10}  {'Full %':>10}")
print("-"*60)
for r_key in RANKS:
    r_label = RANK_LABEL[r_key]
    rank_x_exposure[r_key] = {}
    cells = []
    for period_name, mask in [("no_exposure", NO_EXP), ("partial", PARTIAL), ("full", FULL)]:
        sub = df_full[mask & (df_full.prior_bucket=="new") & (df_full.rank_label==r_label)]
        if len(sub):
            rate = sub.bin_e.mean() * 100
            cells.append(f"{rate:>5.1f}% ({len(sub):,})")
            rank_x_exposure[r_key][period_name] = {"n": int(len(sub)), "pct_above_P95": round(float(rate), 2)}
        else:
            cells.append(f"{'—':>10}")
            rank_x_exposure[r_key][period_name] = {"n": 0, "pct_above_P95": None}
    print(f"  {r_label:<22}  " + "  ".join(f"{c:>10}" for c in cells))

# ---- Save consolidated JSON ----
out = {
    "method_note": (
        "First-time submitters are defined as canonical first authors with "
        "zero prior submissions (any author position) across the 2005-2026 "
        "SSWR archive, deduplicated to (canonical_author_id, paper_id) pairs. "
        "Rank is taken from the first author's fa_rank field in "
        "data/corpus_preprocessed.pkl. Analytic window: conf 2010-2026."
    ),
    "n_first_timers_with_rank": int(len(new)),
    "rank_distribution_overall": {
        r: {"n": int(rank_counts.get(r, 0)), "pct": float(rank_pct.get(r, 0))}
        for r in [RANK_LABEL[k] for k in RANKS]
    },
    "career_stage_summary": {
        "early_career_doc_postdoc_assistant_pct":
            round(ec_n / known_total * 100, 1) if known_total else None,
        "mid_career_associate_pct":
            round(mc_n / known_total * 100, 1) if known_total else None,
        "senior_full_pct":
            round(sr_n / known_total * 100, 1) if known_total else None,
        "other_excluded_n": int(oth_n),
    },
    "rank_x_exposure_period_first_timers_n_and_pct": period_results,
    "above_P95_rate_first_timers_by_rank_x_exposure_EditLens_R": rank_x_exposure,
}
out_path = RES / "first_time_submitter_ranks.json"
out_path.write_text(json.dumps(out, indent=2, default=str))
print(f"\nSaved -> {out_path}")
