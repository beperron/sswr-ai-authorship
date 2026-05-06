"""
Pangram-style multi-window scoring with EditLens RoBERTa-large.

Per Gartenberg et al. (2026, §2.1), Pangram processes text in 400-word
windows and reports a word-count-weighted average across windows. EditLens
RoBERTa caps at 512 tokens (~395 words). For SSWR abstracts (median 614
tokens, 95th pct 726, 99th pct 795), this means 91% of abstracts overflow
a single 512-token window.

This script implements Pangram-style multi-window aggregation for EditLens
RoBERTa: split each abstract into non-overlapping ~512-token windows, score
each, and report the word-count-weighted average. Equivalent in spirit to
what Pangram does for multi-segment texts. The previous single-window scoring
is retained for comparison; this is the "Pangram-equivalent" companion.

Output columns:
  score_editlens_mw     : word-count-weighted average across windows
  bucket_editlens_mw    : weighted-average bucket index, then argmax
  n_windows             : number of windows for the abstract
"""

import torch, pandas as pd, json, time, re
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm

# EditLens preprocessing
BOILERPLATE_STARTS = ["Sure","Here","Abstract","Title","I'm happy to help","Certainly"]
def _ws(t): return re.sub(r"\s+", " ", t).strip()
def _think(t):
    if "</think>" in t: return t.split("</think>")[1].strip()
    return t
def _aih(t):
    paragraphs = [p for p in t.split("\n") if p.strip()]
    if not paragraphs: return t
    first = re.sub(r"^[^a-zA-Z0-9]*", "", paragraphs[0])
    if any(first.startswith(p) for p in BOILERPLATE_STARTS) and len(paragraphs) > 1:
        t = "\n".join(paragraphs[1:])
    return t
def editlens_clean(t):
    return _ws(_think(_aih(t)).lower())

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
MODEL_ID = "pangram/editlens_roberta-large"
OUT  = ROOT / "data" / "scores_editlens_roberta_mw.pkl"
META = ROOT / "logs" / "26_editlens_roberta_mw.json"

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {device}")
print("Loading model...")
tok = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(device).eval()
n_buckets = model.config.num_labels
bucket_index = torch.arange(n_buckets, dtype=torch.float32, device=device)

# Window parameters
MAX_LEN = 512                   # RoBERTa native cap
SPECIAL_TOKEN_BUDGET = 2        # CLS + SEP
WINDOW_TOKENS = MAX_LEN - SPECIAL_TOKEN_BUDGET   # 510 content tokens per window

def windows(text):
    """Split text into non-overlapping windows of WINDOW_TOKENS content tokens.
    Returns list of (window_text, window_word_count)."""
    # Use the tokenizer to get the token-IDs without special tokens
    ids = tok(text, add_special_tokens=False, truncation=False)["input_ids"]
    if len(ids) == 0:
        return [("", 0)]
    chunks = []
    for start in range(0, len(ids), WINDOW_TOKENS):
        chunk_ids = ids[start:start + WINDOW_TOKENS]
        chunk_text = tok.decode(chunk_ids, skip_special_tokens=True)
        wc = len(re.findall(r"\b\w+\b", chunk_text))
        chunks.append((chunk_text, wc))
    return chunks

# Load corpus
df = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl").reset_index(drop=True)
df["text_editlens"] = df["text"].apply(editlens_clean)
print(f"Corpus: {len(df):,} abstracts")

BATCH = 16
rows = []
t0 = time.time()
pbar = tqdm(range(0, len(df)), desc="multiwindow")

# Build a flat list of (abstract_idx, window_text, window_wc) and process in batches
flat_windows = []
n_windows_per = []
for i, txt in enumerate(df["text_editlens"]):
    chunks = windows(txt)
    n_windows_per.append(len(chunks))
    for w_text, w_wc in chunks:
        flat_windows.append((i, w_text, w_wc))

print(f"Total windows: {len(flat_windows):,} ({len(flat_windows)/len(df):.2f} per abstract on average)")
n_windows_dist = pd.Series(n_windows_per).value_counts().sort_index()
print(f"n_windows distribution: {n_windows_dist.to_dict()}")

# Score windows in batches
window_scores = [None] * len(flat_windows)     # continuous scores
window_buckets = [None] * len(flat_windows)
window_probs = [None] * len(flat_windows)

with torch.inference_mode():
    pbar2 = tqdm(range(0, len(flat_windows), BATCH), desc="scoring")
    for bi in pbar2:
        batch = flat_windows[bi:bi+BATCH]
        texts = [w[1] for w in batch]
        enc = tok(texts, padding=True, truncation=True,
                  max_length=MAX_LEN, return_tensors="pt").to(device)
        logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1)
        scores = (probs * bucket_index).sum(-1) / (n_buckets - 1)
        bargmax = probs.argmax(-1)
        for k, (orig_i, _, wc) in enumerate(batch):
            window_scores[bi + k] = float(scores[k].item())
            window_buckets[bi + k] = int(bargmax[k].item())
            window_probs[bi + k] = probs[k].cpu().numpy()
        if (bi // BATCH) % 50 == 49:
            pbar2.set_postfix(rate=f"{(bi+BATCH)/(time.time()-t0):.1f} wins/s")

# Aggregate per abstract: word-count-weighted average
agg = []
ptr = 0
for i, n in enumerate(n_windows_per):
    sub_scores = window_scores[ptr:ptr+n]
    sub_wcs = [flat_windows[ptr+k][2] for k in range(n)]
    total_wc = max(1, sum(sub_wcs))
    weighted_score = sum(s*w for s, w in zip(sub_scores, sub_wcs)) / total_wc
    # Aggregate probs the same way
    sub_probs = [window_probs[ptr+k] for k in range(n)]
    weighted_probs = sum(p*w for p, w in zip(sub_probs, sub_wcs)) / total_wc
    agg_bucket = int(weighted_probs.argmax())
    agg.append({
        "id": df.loc[i, "id"],
        "score_editlens_mw": weighted_score,
        "bucket_editlens_mw": agg_bucket,
        "n_windows": n,
    })
    ptr += n

agg_df = pd.DataFrame(agg).set_index("id")
df_out = df.merge(agg_df, on="id")
print("\n=== Multi-window score distribution ===")
print(df_out["score_editlens_mw"].describe(percentiles=[.05,.25,.5,.75,.9,.95,.99]).round(4).to_string())
print("\n=== Multi-window bucket distribution ===")
print(df_out["bucket_editlens_mw"].value_counts().sort_index().to_string())

df_out.to_pickle(OUT)
META.parent.mkdir(parents=True, exist_ok=True)
META.write_text(json.dumps({
    "model_id": MODEL_ID,
    "device": str(device),
    "window_tokens": WINDOW_TOKENS,
    "batch_size": BATCH,
    "n_abstracts": int(len(df_out)),
    "n_windows_total": int(len(flat_windows)),
    "mean_windows_per_abstract": float(len(flat_windows)/len(df_out)),
    "score_summary": df_out["score_editlens_mw"].describe().round(6).to_dict(),
    "bucket_distribution": df_out["bucket_editlens_mw"].value_counts().sort_index().to_dict(),
    "elapsed_seconds": float(time.time() - t0),
}, indent=2, default=str))
print(f"\nSaved -> {OUT}")
