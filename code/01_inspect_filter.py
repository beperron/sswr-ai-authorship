"""
Step 1 — Load corpus, inspect, apply scientific-format filter.

User instruction: 'scientific format' inclusion only. Exclude flash talks, workshops,
withdrawn / short abstracts. The CSV does not carry an explicit format field, so we
operationalize via:
  - word count >= 100  (Pangram min recommendation; also excludes flash-talk and
    withdrawn / placeholder records)
  - non-empty title and abstract
  - no duplicate abstracts within year (defensive)

We retain methodology classification (quantitative, qualitative, mixed_methods,
reviews) for the qual-vs-quant comparison required by the user; it is NOT used to
stratify the primary corpus.
"""

import pandas as pd
import numpy as np
import re
import json
from pathlib import Path

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
RAW = ROOT / "data" / "sswr_papers.csv"
OUT = ROOT / "data" / "corpus_filtered.pkl"
LOG = ROOT / "logs" / "01_filter_log.json"

print("Loading corpus...")
df = pd.read_csv(RAW, dtype=str, keep_default_na=False)
print(f"Raw rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")
print(f"Years present: {sorted(df['year'].unique())}")

WORD_RE = re.compile(r"\b\w+\b")
def word_count(s: str) -> int:
    return len(WORD_RE.findall(s or ""))

# Per-year raw counts (cross-check against metadata.json)
print("\nRaw count by year:")
print(df.groupby("year").size().to_string())

# Initial stats
df["abstract_wc"] = df["abstract"].apply(word_count)
df["title_wc"] = df["title"].apply(word_count)
print("\nAbstract word-count distribution (raw):")
print(df["abstract_wc"].describe(percentiles=[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).round(1).to_string())

print("\nMethodology distribution (raw):")
print(df["methodology"].value_counts(dropna=False).to_string())

# ---- FILTERS ----
n0 = len(df)
log = {"raw_rows": n0}

# 1. Drop rows with empty abstract
mask_nonempty = df["abstract"].astype(str).str.strip().ne("")
df = df[mask_nonempty].copy()
log["dropped_empty_abstract"] = n0 - len(df)
n1 = len(df)
print(f"\nAfter empty-abstract drop: {n1:,} (-{n0-n1:,})")

# 2. Drop short / flash / workshop / withdrawn (word count < 100)
SHORT_THRESHOLD = 100
mask_long = df["abstract_wc"] >= SHORT_THRESHOLD
short_n = (~mask_long).sum()
print(f"\nAbstracts < {SHORT_THRESHOLD} words (excluded as flash/workshop/withdrawn proxy): {short_n:,} ({short_n/n1*100:.1f}%)")
print("Per-year breakdown of excluded short abstracts:")
print(df[~mask_long].groupby("year").size().to_string())
df = df[mask_long].copy()
log["short_threshold_words"] = SHORT_THRESHOLD
log["dropped_short_abstract"] = int(short_n)
n2 = len(df)

# 3. Drop within-year duplicates on abstract text
dup_mask = df.duplicated(subset=["year", "abstract"], keep="first")
print(f"\nWithin-year duplicate abstracts: {dup_mask.sum():,}")
df = df[~dup_mask].copy()
log["dropped_within_year_duplicates"] = int(dup_mask.sum())
n3 = len(df)

# 4. Coerce year to int
df["year"] = df["year"].astype(int)

# 5. Submission cycle: SSWR conference Jan year X; submission deadline April year X-1
df["submission_year"] = df["year"] - 1

# Final counts
print(f"\nFINAL N: {len(df):,} (from {n0:,}; net drop {n0-len(df):,} = {(n0-len(df))/n0*100:.1f}%)")
print("\nFinal counts by conference year:")
print(df.groupby("year").size().to_string())
print("\nFinal methodology distribution:")
print(df["methodology"].value_counts(dropna=False).to_string())

# Save
df.to_pickle(OUT)
log["final_n"] = len(df)
log["per_year_final"] = df.groupby("year").size().to_dict()
log["per_methodology_final"] = df["methodology"].value_counts(dropna=False).to_dict()
log["wc_summary"] = df["abstract_wc"].describe().round(2).to_dict()
LOG.parent.mkdir(parents=True, exist_ok=True)
LOG.write_text(json.dumps(log, indent=2, default=str))
print(f"\nSaved filtered corpus -> {OUT}")
print(f"Saved filter log     -> {LOG}")
