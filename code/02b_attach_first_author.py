"""
Attach first-author rank to each paper.  Run AFTER preprocess, BEFORE
calibrate/labels.  Uses position_normalized; collapses to:

  assistant   = assistant_professor
  associate   = associate_professor
  full        = full_professor
  postdoc     = postdoctoral
  doctoral    = doctoral_student
  other       = everything else (research staff, MA students, instructors,
                practitioner, unknown, etc.)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
authors = pd.read_csv(ROOT / "data" / "sswr_paper_authors.csv", dtype=str,
                      keep_default_na=False)
firsts = authors[authors["author_order"] == "1"][["paper_id", "position_normalized"]]
firsts = firsts.rename(columns={"position_normalized": "fa_position_norm"})

RANK_MAP = {
    "assistant_professor": "assistant",
    "associate_professor": "associate",
    "full_professor":      "full",
    "postdoctoral":        "postdoc",
    "doctoral_student":    "doctoral",
}
firsts["fa_rank"] = firsts["fa_position_norm"].map(RANK_MAP).fillna("other")

# Drop within-paper duplicates if any
firsts = firsts.drop_duplicates("paper_id")

print("First-author rank distribution (first authors of all papers):")
print(firsts["fa_rank"].value_counts().to_string())

df = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl")
print(f"\nCorpus rows before merge: {len(df):,}")
df = df.merge(firsts, left_on="id", right_on="paper_id", how="left").drop(columns=["paper_id"])
df["fa_rank"] = df["fa_rank"].fillna("other")
df["fa_position_norm"] = df["fa_position_norm"].fillna("unknown")
print(f"Corpus rows after merge:  {len(df):,}")
print("\nFirst-author rank in retained corpus:")
print(df["fa_rank"].value_counts().to_string())

df.to_pickle(ROOT / "data" / "corpus_preprocessed.pkl")
print(f"\n-> {ROOT / 'data' / 'corpus_preprocessed.pkl'}  (with fa_rank column)")
