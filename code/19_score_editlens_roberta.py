"""
Score the SSWR corpus with pangram/editlens_roberta-large.

EditLens architecture:
  RobertaForSequenceClassification with 4 buckets (LABEL_0 .. LABEL_3).
  Bucket 0 = fully human; Bucket 3 = fully AI-generated.
  Buckets 1 and 2 are intermediate AI-edited levels.

  continuous score (in [0,1]) = (sum_i i * p_i) / (n_buckets - 1)
                              = expected bucket index / 3

We save:
  - score_editlens          : continuous [0,1]
  - bucket_editlens         : argmax bucket (0..3)
  - p_human, p_light, p_heavy, p_ai : per-bucket softmax probabilities

This gives us both the percentile-anchored continuous outcome (for the primary
analysis) and the native 4-class breakdown (for the Gartenberg-style category
trajectory).
"""

import torch, pandas as pd, json, time, re
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm

# EditLens's clean_text preprocessing — must be applied before scoring or the
# model is out-of-distribution.  Source: pangramlabs/EditLens scripts/preprocess.py
BOILERPLATE_STARTS = ["Sure", "Here", "Abstract", "Title", "I'm happy to help", "Certainly"]

def _normalize_whitespace(t): return re.sub(r"\s+", " ", t).strip()
def _remove_think_tag(t):
    if "</think>" in t: return t.split("</think>")[1].strip()
    return t
def _remove_ai_header(t):
    paragraphs = [p for p in t.split("\n") if p.strip()]
    if not paragraphs: return t
    first = re.sub(r"^[^a-zA-Z0-9]*", "", paragraphs[0])
    if any(first.startswith(p) for p in BOILERPLATE_STARTS) and len(paragraphs) > 1:
        t = "\n".join(paragraphs[1:])
    return t
def editlens_clean_text(t: str) -> str:
    """Match EditLens's training-time preprocessing (without emoji handling
    since SSWR abstracts contain no emojis)."""
    t = _remove_think_tag(t)
    t = _remove_ai_header(t)
    t = t.lower()                       # critical: model trained on lowercased
    t = _normalize_whitespace(t)
    return t

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
MODEL_ID = "pangram/editlens_roberta-large"
OUT  = ROOT / "data" / "scores_editlens_roberta.pkl"
META = ROOT / "logs" / "19_editlens_roberta_scoring.json"

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {device}")
print(f"Model:  {MODEL_ID}")

print("Loading model...")
tok = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(device).eval()
n_buckets = model.config.num_labels
print(f"n_buckets: {n_buckets}")
print(f"id2label : {model.config.id2label}")

# Load preprocessed corpus and apply EditLens-specific clean_text
df = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl").reset_index(drop=True)
print(f"Corpus: {len(df):,} abstracts")
print("Applying EditLens clean_text preprocessing (lowercase + boilerplate strip)...")
df["text_editlens"] = df["text"].apply(editlens_clean_text)

BATCH = 16
MAX_LEN = 512  # RoBERTa native
bucket_index = torch.arange(n_buckets, dtype=torch.float32, device=device)

rows = []
t0 = time.time()
pbar = tqdm(range(0, len(df), BATCH), desc="scoring")
with torch.inference_mode():
    for i in pbar:
        batch = df.iloc[i:i+BATCH]
        enc = tok(list(batch["text_editlens"]), padding=True, truncation=True,
                  max_length=MAX_LEN, return_tensors="pt").to(device)
        logits = model(**enc).logits                        # (B, 4)
        probs = torch.softmax(logits, dim=-1)                # (B, 4)
        # continuous score = E[bucket] / (n-1)
        score = (probs * bucket_index).sum(dim=-1) / (n_buckets - 1)
        bucket_argmax = probs.argmax(dim=-1)
        probs_cpu = probs.cpu().numpy()
        score_cpu = score.cpu().numpy()
        argmax_cpu = bucket_argmax.cpu().numpy()
        for orig_idx, s, b, p in zip(batch.index, score_cpu, argmax_cpu, probs_cpu):
            rows.append((orig_idx, float(s), int(b), float(p[0]), float(p[1]), float(p[2]), float(p[3])))
        if (i // BATCH) % 50 == 49:
            pbar.set_postfix(rate=f"{(i+BATCH)/(time.time()-t0):.1f} ab/s")

scores = pd.DataFrame(rows, columns=["idx","score_editlens","bucket_editlens",
                                     "p_human","p_light","p_heavy","p_ai"]).set_index("idx").sort_index()
df_out = df.copy()
for c in scores.columns:
    df_out[c] = scores[c].reindex(df_out.index)

print("\n=== Score distribution ===")
print(df_out["score_editlens"].describe(percentiles=[.05,.25,.5,.75,.9,.95,.99]).round(4).to_string())
print("\n=== Bucket distribution (argmax) ===")
print(df_out["bucket_editlens"].value_counts().sort_index().to_string())

df_out.to_pickle(OUT)
META.parent.mkdir(parents=True, exist_ok=True)
META.write_text(json.dumps({
    "model_id": MODEL_ID,
    "device": str(device),
    "max_length": MAX_LEN,
    "batch_size": BATCH,
    "n_buckets": n_buckets,
    "n_scored": int(df_out["score_editlens"].notna().sum()),
    "score_summary": df_out["score_editlens"].describe().round(6).to_dict(),
    "bucket_distribution": df_out["bucket_editlens"].value_counts().sort_index().to_dict(),
}, indent=2, default=str))
print(f"\nSaved -> {OUT}")
print(f"Meta  -> {META}")
