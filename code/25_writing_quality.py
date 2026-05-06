"""
Writing-quality metrics following Gartenberg et al. (2026) §2.2.

Implemented (Tier 1 + Tier 2 of the strategy proposal):
  Readability:
    - Flesch Reading Ease (textstat)
    - Flesch-Kincaid Grade Level (textstat)
    - Gunning FOG Index (textstat)
    - SMOG Index (textstat)
    - Mean sentence length (textstat)
    - Type-token ratio (manual)
  Style:
    - Nominalization rate (spaCy POS + suffix match)
    - Passive voice rate (spaCy dep parse: nsubjpass / auxpass)
    - Hedging rate (Hyland 2005 list, public)
    - First-person rate (I/we/our/my)

Skipped (require Gartenberg's online appendix to operationalize exactly):
  - Jargon (would need Gartenberg's word list or domain reference corpus)
  - Specificity (multiple operationalizations possible)
"""

import pandas as pd, numpy as np, json, re
from pathlib import Path
import textstat, spacy
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent  # repo root
print("Loading spaCy...")
nlp = spacy.load("en_core_web_sm", disable=["ner"])
nlp.max_length = 200_000

# --- Hyland (2005) academic hedge list (~80 items, public) ---
HEDGE_WORDS = set("""
about apparent apparently appear appeared appears approximately argue argues argued
around assume assumed assumption broadly claim claims could doubt doubtful essentially
estimate estimated frequently general generally guess guessed indicate indicated indicates
indication largely likely mainly may maybe might mostly often partially partly perhaps
plausible plausibly possibility possible possibly potential potentially predict predicted
predicts presumable presumably probable probably putative quite rarely rather relatively
roughly seem seemed seems should slightly somewhat sort speculate speculated speculation
suggest suggested suggestion suggests suppose supposed supposedly suspect tend tends tended
think thought typical typically uncertain unclear unlikely usually virtually would
""".split())

NOMINALIZATION_SUFFIXES = ("tion","sion","ment","ance","ence","ity","ness","ship","ism","hood","age")

FIRST_PERSON = {"i","i'm","i've","i'd","i'll","me","my","mine","myself",
                 "we","we're","we've","we'd","we'll","us","our","ours","ourselves"}

def compute_metrics(text: str):
    """Return a dict of all writing metrics for one abstract."""
    out = {}
    # textstat readability
    try:
        out["flesch_reading_ease"] = textstat.flesch_reading_ease(text)
        out["flesch_kincaid_grade"] = textstat.flesch_kincaid_grade(text)
        out["fog_index"] = textstat.gunning_fog(text)
        out["smog_index"] = textstat.smog_index(text)
        out["sent_len_mean"] = textstat.avg_sentence_length(text)
    except Exception:
        for k in ("flesch_reading_ease","flesch_kincaid_grade","fog_index","smog_index","sent_len_mean"):
            out[k] = np.nan

    # spaCy-based metrics
    doc = nlp(text)
    n_tok = sum(1 for t in doc if not t.is_space)
    n_alpha = sum(1 for t in doc if t.is_alpha)
    if n_alpha == 0:
        for k in ("nominalization_rate","passive_rate","hedge_rate","first_person_rate","ttr"):
            out[k] = np.nan
        return out

    # Type-Token Ratio (lowercased alphabetic tokens)
    alpha_lower = [t.text.lower() for t in doc if t.is_alpha]
    out["ttr"] = len(set(alpha_lower)) / len(alpha_lower) if alpha_lower else np.nan

    # Nominalization: noun tokens whose lowercased lemma ends in a nominalization suffix
    nominalizations = sum(1 for t in doc
                          if t.pos_ == "NOUN" and t.lemma_.lower().endswith(NOMINALIZATION_SUFFIXES))
    out["nominalization_rate"] = nominalizations / n_alpha

    # Passive voice: count of dependency labels indicating passive
    passive = sum(1 for t in doc if t.dep_ in ("auxpass", "nsubjpass"))
    n_clauses = max(1, sum(1 for t in doc if t.dep_ in ("ROOT", "ccomp", "advcl", "relcl", "xcomp")))
    out["passive_rate"] = passive / n_clauses

    # Hedge rate (lowercased word match against Hyland list)
    hedges = sum(1 for w in alpha_lower if w in HEDGE_WORDS)
    out["hedge_rate"] = hedges / n_alpha

    # First-person rate
    fp = sum(1 for w in alpha_lower if w in FIRST_PERSON)
    out["first_person_rate"] = fp / n_alpha

    return out


def main():
    df = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl").reset_index(drop=True)
    print(f"Computing writing-quality metrics on {len(df):,} abstracts...")

    rows = []
    for idx, text in tqdm(zip(df.index, df["text"]), total=len(df)):
        m = compute_metrics(text)
        m["id"] = df.loc[idx, "id"]
        rows.append(m)

    metrics = pd.DataFrame(rows).set_index("id")
    print("\n=== Score distribution by metric ===")
    print(metrics.describe(percentiles=[.25,.5,.75,.95]).round(3).to_string())
    metrics.to_pickle(ROOT / "data" / "writing_quality.pkl")
    metrics.to_csv(ROOT / "results" / "writing_quality_per_abstract.csv")
    print(f"\nSaved -> data/writing_quality.pkl ({len(metrics):,} rows)")


if __name__ == "__main__":
    main()
