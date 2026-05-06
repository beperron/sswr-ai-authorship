"""
Step 2 — Deterministic preprocessing applied uniformly across all years.

  * NFKC normalization
  * Smart-quote / dash normalization
  * Whitespace collapse
  * Strip leading 'Abstract:' / 'BACKGROUND:' boilerplate? -> NO. Per protocol §4.6,
    structured-abstract section labels are RETAINED because their distribution is a
    stylistic feature whose temporal trend we do NOT want preprocessing to absorb.
  * Lowercase? -> NO. Detector tokenizers are cased; lowercasing would change scores.
  * Length cap is handled at tokenization time (truncation), not here.

Outputs the same dataframe with a new column `text` = preprocessed abstract.
"""

import pandas as pd
import unicodedata, re
from pathlib import Path

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
df = pd.read_pickle(ROOT / "data" / "corpus_filtered.pkl")

QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"'}
DASHES = {"–": "-", "—": "-"}

def preprocess(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for k, v in QUOTES.items(): s = s.replace(k, v)
    for k, v in DASHES.items(): s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s).strip()
    return s

df["text"] = df["abstract"].astype(str).apply(preprocess)
df["text_wc"] = df["text"].apply(lambda s: len(re.findall(r"\b\w+\b", s)))

print(f"Preprocessed {len(df):,} abstracts.")
print(df[["abstract_wc", "text_wc"]].describe().round(1).to_string())

df.to_pickle(ROOT / "data" / "corpus_preprocessed.pkl")
print(f"-> {ROOT / 'data' / 'corpus_preprocessed.pkl'}")
