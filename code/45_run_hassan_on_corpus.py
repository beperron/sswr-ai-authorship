"""
Apply the Hassan analyzer (code/44_hassan_analyzer.py) to the SSWR corpus
and compare its outputs against the existing writing-quality scoring at
code/25_writing_quality.py.

EXCLUSIONS (per user instruction):
  - Jargon detection is NOT applied. The MANAGEMENT_JARGON dictionary is
    domain-specific to management/organization-science vocabulary and does
    not transfer to social work without re-derivation by social-work
    subject-matter experts.
  - Specificity is NOT applied as-is. The SPECIFIC_METHODS list is
    discipline-portable but the THEORETICAL_MARKERS list contains
    economics-specific terminology ("Nash equilibrium", "Pareto",
    "first-order condition", etc.) that would systematically deflate
    social-work specificity scores.

INCLUDED:
  - Readability metrics (Flesch RE, FK Grade, FOG, SMOG, ARI) — language-neutral
  - Nominalization detection — language-neutral
  - Passive-voice detection — language-neutral
  - Hedging detection (Hyland 2005 list) — language-neutral

OUTPUTS:
  - data/scores_hassan.pkl: per-abstract Hassan metrics
  - results/hassan_vs_existing_comparison.json: agreement statistics
"""

import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
sys.path.insert(0, str(ROOT / "code"))

# Import the Hassan analyzer functions we need
import importlib.util
spec = importlib.util.spec_from_file_location(
    "hassan", str(ROOT / "code" / "44_hassan_analyzer.py")
)
hassan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hassan)

# Load the corpus
corpus = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl")
existing = pd.read_pickle(ROOT / "data" / "writing_quality.pkl")
print(f"Corpus N = {len(corpus):,}")
print(f"Existing writing-quality N = {len(existing):,}")

# Restrict to analytic window 2010-2026
corpus = corpus[corpus.year >= 2010].copy()
print(f"Restricted to conf 2010-2026: N = {len(corpus):,}")

# Identify text column
text_col = None
for c in ("text_clean", "abstract_text", "text", "abstract"):
    if c in corpus.columns:
        text_col = c
        break
if text_col is None:
    raise RuntimeError(f"No text column found. Available: {list(corpus.columns)}")
print(f"Using text column: {text_col!r}")

# Run the Hassan analyzer on each abstract, capturing only the metrics
# we are keeping. Skip jargon and specificity outright.
records = []
print(f"\nScoring {len(corpus):,} abstracts with Hassan analyzer...")
for i, row in enumerate(corpus.itertuples(index=False)):
    text = getattr(row, text_col)
    if not isinstance(text, str) or len(text.strip()) < 50:
        continue

    sentences = hassan.tokenize_sentences(text)
    words = hassan.tokenize_words(text)
    n_sent = max(1, len(sentences))
    n_word = max(1, len(words))

    trad = hassan.calculate_traditional_readability(text)
    noms = hassan.detect_nominalizations(text)
    passive = hassan.detect_passive_voice(sentences)
    hedges = hassan.detect_hedges(text)

    records.append({
        "id": row.id,
        "year": row.year,
        # Readability (Hassan implementations)
        "hassan_fre":   trad["flesch_reading_ease"],
        "hassan_fk":    trad["flesch_kincaid_grade"],
        "hassan_fog":   trad["gunning_fog_index"],
        "hassan_smog":  trad["smog_index"],
        "hassan_ari":   trad["automated_readability_index"],
        # Style metrics
        "hassan_nom_density":   round(len(noms) / n_sent, 3),
        "hassan_nom_ratio":     round(len(noms) / n_word, 4),
        "hassan_passive_ratio": round(sum(passive) / n_sent, 3),
        "hassan_hedge_density": round(len(hedges) / n_sent, 3),
        # Word/sentence stats
        "hassan_n_words":     n_word,
        "hassan_n_sentences": n_sent,
    })
    if (i + 1) % 5000 == 0:
        print(f"  {i+1:,} / {len(corpus):,}")

hassan_df = pd.DataFrame(records)
hassan_df.to_pickle(ROOT / "data" / "scores_hassan.pkl")
print(f"\nSaved -> data/scores_hassan.pkl (N = {len(hassan_df):,})")

# Compare to existing writing-quality scores
print("\n" + "="*70)
print("COMPARISON: Hassan vs existing (code/25_writing_quality.py)")
print("="*70)
merged = hassan_df.merge(existing, on="id", how="inner")
print(f"Joined N = {len(merged):,}")

mapping = {
    ("hassan_fre",  "flesch_reading_ease"):    "Flesch Reading Ease",
    ("hassan_fk",   "flesch_kincaid_grade"):   "Flesch-Kincaid Grade",
    ("hassan_fog",  "fog_index"):              "Gunning FOG",
    ("hassan_smog", "smog_index"):             "SMOG",
    ("hassan_passive_ratio", "passive_rate"):  "Passive voice rate",
    ("hassan_hedge_density", "hedge_rate"):    "Hedge rate",
    ("hassan_nom_ratio", "nominalization_rate"): "Nominalization rate",
}

comparison = {}
print(f"\n{'Metric':<24} {'r':>7} {'Hassan mean':>14} {'Existing mean':>16} {'mean diff':>12}")
print("-" * 76)
for (h_col, e_col), label in mapping.items():
    if h_col not in merged.columns or e_col not in merged.columns:
        continue
    hv = merged[h_col].astype(float)
    ev = merged[e_col].astype(float)
    mask = hv.notna() & ev.notna()
    if mask.sum() < 10:
        continue
    r, _ = pearsonr(hv[mask], ev[mask])
    h_mean = float(hv[mask].mean())
    e_mean = float(ev[mask].mean())
    diff = h_mean - e_mean
    print(f"  {label:<22} {r:>7.3f} {h_mean:>14.4f} {e_mean:>16.4f} {diff:>+12.4f}")
    comparison[label] = {
        "pearson_r": float(r),
        "n": int(mask.sum()),
        "hassan_mean": h_mean,
        "existing_mean": e_mean,
        "mean_diff": diff,
    }

(ROOT / "results" / "hassan_vs_existing_comparison.json").write_text(
    json.dumps(comparison, indent=2)
)
print(f"\nSaved -> results/hassan_vs_existing_comparison.json")
