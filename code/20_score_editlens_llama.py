"""
Score the SSWR corpus with pangram/editlens_Llama-3.2-3B.

This is a PEFT/LoRA adapter on top of meta-llama/Llama-3.2-3B.
Adapter config (verified):
  base_model_name_or_path: meta-llama/Llama-3.2-3B
  task_type: SEQ_CLS
  modules_to_save: ["score", "classifier", "score"]   (full-weight, not LoRA delta)
  target_modules: q/k/v/o_proj, gate/up/down_proj
  r=8, lora_alpha=16, lora_dropout=0.05

Loading recipe (matches Pangram's inference.py without bitsandbytes 4-bit
quantization, since bitsandbytes does not support MPS):
  1. Load base meta-llama/Llama-3.2-3B as AutoModelForSequenceClassification
     with num_labels=4 (matching EditLens's 4-bucket head).
  2. Apply PEFT adapter via PeftModel.from_pretrained.
  3. Inference with same EditLens clean_text preprocessing.

Memory: 3B params in fp32 = ~12 GB; in fp16 = ~6 GB. We load in fp16 and run
on MPS in fp16 (the Llama backbone supports MPS+fp16 cleanly, unlike the
DeBERTa attention kernel that crashed earlier).

Throughput on MPS: ~3-8 abstracts/sec expected (rough estimate; 3B model
on M-series silicon).
"""

import torch, pandas as pd, json, time, re
import torch.nn as nn
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel
from tqdm import tqdm

# Pangram replaces the standard Llama score head with a LayerNorm + Linear
# combo for training stability ("NormedLinear" in their EditLens repo).
# Source: pangramlabs/EditLens scripts/train.py
class NormedLinear(nn.Module):
    def __init__(self, hidden_size, num_labels, device=None, dtype=None):
        super().__init__()
        self.norm = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.linear = nn.Linear(hidden_size, num_labels, bias=False, device=device, dtype=dtype)
    def forward(self, x):
        return self.linear(self.norm(x))

# ---- EditLens preprocessing (same as roberta script) ----
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
    t = _remove_think_tag(t)
    t = _remove_ai_header(t)
    t = t.lower()
    t = _normalize_whitespace(t)
    return t

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
ADAPTER_ID = "pangram/editlens_Llama-3.2-3B"
BASE_ID    = "meta-llama/Llama-3.2-3B"
OUT  = ROOT / "data" / "scores_editlens_llama.pkl"
META = ROOT / "logs" / "20_editlens_llama_scoring.json"
CKPT = ROOT / "checkpoints" / "scores_editlens_llama_partial.pkl"

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {device}")
print(f"Adapter: {ADAPTER_ID}")
print(f"Base:    {BASE_ID}")

print("Loading base model in fp16...")
tok = AutoTokenizer.from_pretrained(BASE_ID)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
base = AutoModelForSequenceClassification.from_pretrained(
    BASE_ID, num_labels=4, torch_dtype=torch.float16
)
base.config.pad_token_id = tok.pad_token_id

# Replace the standard score head with NormedLinear so the adapter weights
# slot in correctly.
hidden_size = base.config.hidden_size
base.score = NormedLinear(hidden_size, 4, dtype=torch.float16)
print(f"Replaced score head with NormedLinear (hidden_size={hidden_size}, num_labels=4)")

print("Applying LoRA adapter...")
model = PeftModel.from_pretrained(base, ADAPTER_ID, torch_dtype=torch.float16)
model = model.merge_and_unload()    # merge LoRA into base for faster inference
model = model.to(device).eval()
n_buckets = model.config.num_labels
print(f"n_buckets: {n_buckets}")

# Load corpus
df = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl").reset_index(drop=True)
print(f"Corpus: {len(df):,} abstracts")
df["text_editlens"] = df["text"].apply(editlens_clean_text)

if CKPT.exists():
    done = pd.read_pickle(CKPT)
    print(f"Resuming from checkpoint: {len(done):,} already scored")
    todo_idx = df.index.difference(done.index)
    df_todo = df.loc[todo_idx]
else:
    done = pd.DataFrame(columns=["score_editlens_llama","bucket_editlens_llama",
                                 "p_human","p_light","p_heavy","p_ai"]).set_index(pd.Index([], dtype=int))
    df_todo = df

BATCH = 4              # 3B model needs smaller batches than RoBERTa
MAX_LEN = 1024         # Llama supports much longer context than RoBERTa
bucket_index = torch.arange(n_buckets, dtype=torch.float16, device=device)

if len(df_todo):
    rows = []
    t0 = time.time()
    pbar = tqdm(range(0, len(df_todo), BATCH), desc="scoring")
    with torch.inference_mode():
        for i in pbar:
            batch = df_todo.iloc[i:i+BATCH]
            enc = tok(list(batch["text_editlens"]), padding=True, truncation=True,
                      max_length=MAX_LEN, return_tensors="pt").to(device)
            logits = model(**enc).logits.float()             # cast back to fp32 for softmax
            probs = torch.softmax(logits, dim=-1)
            score = (probs * bucket_index.float()).sum(-1) / (n_buckets - 1)
            argmax = probs.argmax(-1)
            for orig_idx, s, b, p in zip(batch.index,
                                         score.cpu().numpy(),
                                         argmax.cpu().numpy(),
                                         probs.cpu().numpy()):
                rows.append((orig_idx, float(s), int(b),
                             float(p[0]), float(p[1]), float(p[2]), float(p[3])))
            if (i // BATCH) % 100 == 99:
                tmp = pd.DataFrame(rows, columns=["idx","score_editlens_llama","bucket_editlens_llama",
                                                  "p_human","p_light","p_heavy","p_ai"]).set_index("idx")
                pd.concat([done, tmp]).to_pickle(CKPT)
                pbar.set_postfix(rate=f"{(i+BATCH)/(time.time()-t0):.1f} ab/s")
    new = pd.DataFrame(rows, columns=["idx","score_editlens_llama","bucket_editlens_llama",
                                      "p_human","p_light","p_heavy","p_ai"]).set_index("idx")
    full_scores = pd.concat([done, new]).sort_index()
else:
    full_scores = done.sort_index()

df_out = df.copy()
for c in full_scores.columns:
    df_out[c] = full_scores[c].reindex(df_out.index)

print("\n=== Score distribution ===")
print(df_out["score_editlens_llama"].describe(percentiles=[.05,.25,.5,.75,.9,.95,.99]).round(4).to_string())
print("\n=== Bucket distribution (argmax) ===")
print(df_out["bucket_editlens_llama"].value_counts().sort_index().to_string())

df_out.to_pickle(OUT)
META.parent.mkdir(parents=True, exist_ok=True)
META.write_text(json.dumps({
    "adapter_id": ADAPTER_ID,
    "base_id": BASE_ID,
    "device": str(device),
    "max_length": MAX_LEN,
    "batch_size": BATCH,
    "dtype": "fp16",
    "n_buckets": n_buckets,
    "n_scored": int(df_out["score_editlens_llama"].notna().sum()),
    "score_summary": df_out["score_editlens_llama"].describe().round(6).to_dict(),
    "bucket_distribution": df_out["bucket_editlens_llama"].value_counts().sort_index().to_dict(),
}, indent=2, default=str))
print(f"\nSaved -> {OUT}")
