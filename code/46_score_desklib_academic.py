"""
Re-score the SSWR corpus with desklib/ai-text-detector-academic-v1.01,
using the same configuration as the existing vanilla desklib scoring
(max_length=768, default right-truncation) so the swap is detector-only.

This replaces scores_primary.pkl in the Stage 2 analysis with the
academic-tuned variant. The academic variant is a fine-tuned
microsoft/deberta-v3-large model trained on academic-domain data and is
the appropriate choice for an SSWR conference-abstract corpus.
"""

import torch, json, time
import torch.nn as nn
import pandas as pd
from pathlib import Path
from transformers import AutoTokenizer, AutoModel, AutoConfig
from tqdm import tqdm
from safetensors.torch import load_file
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent.parent  # repo root
MODEL_ID = "desklib/ai-text-detector-academic-v1.01"
OUT_PKL  = ROOT / "data" / "scores_primary_academic.pkl"
CKPT     = ROOT / "checkpoints" / "scores_primary_academic_partial.pkl"
META     = ROOT / "logs" / "46_primary_academic_scoring.json"

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Device: {device}")
print(f"Model: {MODEL_ID}")

class AIDetector(nn.Module):
    def __init__(self, model_id):
        super().__init__()
        self.config = AutoConfig.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id)
        self.classifier = nn.Linear(self.config.hidden_size, 1)
    def forward(self, input_ids, attention_mask):
        out = self.model(input_ids=input_ids, attention_mask=attention_mask)
        h = out.last_hidden_state
        mask = attention_mask.unsqueeze(-1).float()
        pooled = (h * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        logit = self.classifier(pooled)
        return logit.squeeze(-1)

print("Loading tokenizer + model + safetensors classifier head...")
tok = AutoTokenizer.from_pretrained(MODEL_ID)
sd_path = hf_hub_download(MODEL_ID, "model.safetensors")
sd = load_file(sd_path)
classifier_keys = [k for k in sd if "classifier" in k.lower()]
print(f"Classifier keys: {classifier_keys}")

model = AIDetector(MODEL_ID)
missing, unexpected = model.load_state_dict(sd, strict=False)
print(f"State dict load -> missing={len(missing)} unexpected={len(unexpected)}")
if missing: print("  First 5 missing:", missing[:5])
if unexpected: print("  First 5 unexpected:", unexpected[:5])
model.to(device).eval()

print(f"classifier.weight norm: {float(model.classifier.weight.norm().item()):.4f}")
print(f"classifier.bias:        {float(model.classifier.bias.item()):.4f}")

df = pd.read_pickle(ROOT / "data" / "corpus_preprocessed.pkl").reset_index(drop=True)
print(f"\nCorpus: {len(df):,} abstracts")

if CKPT.exists():
    done = pd.read_pickle(CKPT)
    print(f"Resuming from checkpoint: {len(done):,} already scored")
    todo_idx = df.index.difference(done.index)
    df_todo = df.loc[todo_idx]
else:
    done = pd.DataFrame(columns=["score_academic_primary"]).set_index(
        pd.Index([], dtype=int, name="idx"))
    df_todo = df

if len(df_todo):
    BATCH = 16
    MAX_LEN = 768  # match vanilla desklib config exactly
    rows = []
    t0 = time.time()
    pbar = tqdm(range(0, len(df_todo), BATCH), desc="scoring")
    with torch.inference_mode():
        for i in pbar:
            batch = df_todo.iloc[i:i+BATCH]
            enc = tok(list(batch["text"]), padding=True, truncation=True,
                      max_length=MAX_LEN, return_tensors="pt").to(device)
            logits = model(enc["input_ids"], enc["attention_mask"])
            probs = torch.sigmoid(logits).float().cpu().numpy()
            for orig_idx, score in zip(batch.index, probs):
                rows.append((orig_idx, float(score)))
            if (i // BATCH) % 50 == 49:
                tmp = pd.DataFrame(rows, columns=["idx", "score_academic_primary"]).set_index("idx")
                full = pd.concat([done, tmp])
                full.to_pickle(CKPT)
                pbar.set_postfix(rate=f"{(i+BATCH)/(time.time()-t0):.1f} ab/s")
    new = pd.DataFrame(rows, columns=["idx", "score_academic_primary"]).set_index("idx")
    full_scores = pd.concat([done, new]).sort_index()
else:
    full_scores = done.sort_index()

df_out = df.copy()
df_out["score_primary"] = full_scores["score_academic_primary"].reindex(df_out.index)
# Note: we keep the column name as "score_primary" so existing analysis
# scripts that expect it can be pointed at this file by path.
print("\nScore summary:")
print(df_out["score_primary"].describe().round(4).to_string())
df_out.to_pickle(OUT_PKL)
print(f"\nSaved -> {OUT_PKL}")

META.parent.mkdir(parents=True, exist_ok=True)
META.write_text(json.dumps({
    "model_id": MODEL_ID,
    "device": str(device),
    "max_length": 768,
    "truncation_side": "default (right; keeps front of text)",
    "batch_size": 16,
    "n_scored": int(df_out["score_primary"].notna().sum()),
    "score_summary": df_out["score_primary"].describe().round(6).to_dict(),
    "swap_note": ("Replaces vanilla desklib (ai-text-detector-v1.01) with "
                  "academic-tuned variant (ai-text-detector-academic-v1.01) "
                  "for the Stage 2 cross-family triangulation. Same backbone "
                  "(microsoft/deberta-v3-large), same config (max_length=768, "
                  "default truncation), different fine-tuning corpus."),
}, indent=2, default=str))
print(f"Meta saved -> {META}")
