"""
Apply the main-analysis numbers (academic-tuned desklib + 2010-2017 calibration)
into the manuscript markdown source by text-replacing the affected fields.

Reads:
  results/main_analysis_results.json

Updates the manuscript in place. Run code/47_main_analysis.py first
to populate the JSON.
"""

import json, re
from pathlib import Path

ROOT = Path("/Users/beperron/Desktop/AI-SSWR")
MD   = ROOT / "reports" / "STAGE_2_REPORT.md"
JSON = ROOT / "results" / "main_analysis_results.json"

if not JSON.exists():
    raise SystemExit(f"Missing {JSON} — run code/47_main_analysis.py first")

R = json.loads(JSON.read_text())
text = MD.read_text()

# ---- New numbers ----
P95_e   = R["P95"]["EditLens_R_single"]
P95_emw = R["P95"]["EditLens_R_multi"]
P95_l   = R["P95"]["EditLens_Llama"]
P95_d   = R["P95"]["desklib_academic"]

h1_e = R["h1_step"]["EditLens RoBERTa-large"]
h1_l = R["h1_step"]["EditLens Llama-3.2-3B"]
h1_d = R["h1_step"]["desklib academic"]

# Yearly proportions for table
yearly = {row["year"]: row for row in R["yearly"]}

k = R["cohen_kappa"]
rr = R["pearson_r_detectors"]

# ---- Update calibration thresholds line ----
old_thresholds = re.search(
    r"The thresholds are EditLens RoBERTa-large \*P\*₉₅ = [0-9.]+ \(single-window\) and [0-9.]+ \(multi-window aggregate\); EditLens Llama-3\.2-3B \*P\*₉₅ = [0-9.]+; desklib \*P\*₉₅ = [0-9.]+\.",
    text,
)
if old_thresholds:
    new_line = (f"The thresholds are EditLens RoBERTa-large *P*₉₅ = {P95_e:.3f} "
                f"(single-window) and {P95_emw:.3f} (multi-window aggregate); "
                f"EditLens Llama-3.2-3B *P*₉₅ = {P95_l:.3f}; "
                f"desklib academic *P*₉₅ = {P95_d:.3f}.")
    text = text.replace(old_thresholds.group(0), new_line)
    print(f"[OK] Updated thresholds line")
else:
    print(f"[WARN] thresholds line pattern not matched")

# ---- Update H1 step paragraph (body) ----
e_pp = h1_e["level_pp"]; e_lo = h1_e["ci95_lo_pp"]; e_hi = h1_e["ci95_hi_pp"]
l_pp = h1_l["level_pp"]; l_lo = h1_l["ci95_lo_pp"]; l_hi = h1_l["ci95_hi_pp"]
d_pp = h1_d["level_pp"]; d_lo = h1_d["ci95_lo_pp"]; d_hi = h1_d["ci95_hi_pp"]

body_h1 = re.search(
    r"The segmented regression for the primary detector \(EditLens RoBERTa-large\) yielded a level-change of \+[0-9.]+ percentage points \(95% CI \[\+[0-9.]+, \+[0-9.]+\], \*p\* < \.0001\)\. The EditLens Llama-3\.2-3B variant produced a step of \+[0-9.]+ percentage points \(95% CI \[\+[0-9.]+, \+[0-9.]+\], \*p\* < \.0001\); desklib produced \+[0-9.]+ percentage points \(95% CI \[\+[0-9.]+, \+[0-9.]+\], \*p\* < \.0001\)\.",
    text,
)
if body_h1:
    new_h1 = (f"The segmented regression for the primary detector (EditLens RoBERTa-large) "
              f"yielded a level-change of {e_pp:+.1f} percentage points (95% CI "
              f"[{e_lo:+.1f}, {e_hi:+.1f}], *p* < .0001). The EditLens Llama-3.2-3B "
              f"variant produced a step of {l_pp:+.1f} percentage points (95% CI "
              f"[{l_lo:+.1f}, {l_hi:+.1f}], *p* < .0001); the academic-tuned desklib "
              f"detector produced {d_pp:+.1f} percentage points (95% CI "
              f"[{d_lo:+.1f}, {d_hi:+.1f}], *p* < .0001).")
    text = text.replace(body_h1.group(0), new_h1)
    print(f"[OK] Updated body H1 sentence")
else:
    print(f"[WARN] body H1 pattern not matched")

# ---- Update Abstract H1 sentence ----
abs_h1 = re.search(
    r"a step of \+[0-9.]+ percentage points \(95% CI \[\+[0-9.]+, \+[0-9.]+\], \*p\* < \.0001\)\. EditLens Llama-3\.2-3B produced a step of \+[0-9.]+ percentage points \(95% CI \[\+[0-9.]+, \+[0-9.]+\], \*p\* < \.0001\); desklib produced \+[0-9.]+ percentage points \(95% CI \[\+[0-9.]+, \+[0-9.]+\], \*p\* < \.0001\)\.",
    text,
)
if abs_h1:
    new_abs = (f"a step of {e_pp:+.1f} percentage points (95% CI "
               f"[{e_lo:+.1f}, {e_hi:+.1f}], *p* < .0001). EditLens Llama-3.2-3B "
               f"produced a step of {l_pp:+.1f} percentage points (95% CI "
               f"[{l_lo:+.1f}, {l_hi:+.1f}], *p* < .0001); the academic-tuned desklib "
               f"detector produced {d_pp:+.1f} percentage points (95% CI "
               f"[{d_lo:+.1f}, {d_hi:+.1f}], *p* < .0001).")
    text = text.replace(abs_h1.group(0), new_abs)
    print(f"[OK] Updated abstract H1 sentence")
else:
    print(f"[WARN] abstract H1 pattern not matched")

# ---- Update yearly Table 2 (back matter) ----
# Rebuild the entire table data section
table_rows = []
for year in sorted(yearly):
    y = yearly[year]
    table_rows.append(f"| {year} | {y['n']:,} | {y['pct_e']:.1f} | {y['pct_l']:.1f} | {y['pct_d']:.1f} |")
new_table_body = "\n".join(table_rows)

# Find existing data rows in Table 2 (rows starting with year 2010-2026)
table_pat = re.compile(r"(\| 2010 \|.*?\| 2026 \|[^\n]*)", re.DOTALL)
m = table_pat.search(text)
if m:
    text = text.replace(m.group(0), new_table_body)
    print(f"[OK] Updated Table 2 yearly proportions")
else:
    print(f"[WARN] Table 2 yearly rows pattern not matched")

# ---- Update Table 2 header column ----
text = text.replace(
    "| Conference year | *n* | EditLens RoBERTa-large | EditLens Llama-3.2-3B | desklib |",
    "| Conference year | *n* | EditLens RoBERTa-large | EditLens Llama-3.2-3B | desklib academic |"
)
print(f"[OK] Updated Table 2 header")

# ---- Update Table 2 caption ----
text = re.sub(
    r"By conference 2026 the percentage of abstracts above threshold ranges from [0-9.]+% \(desklib\) to [0-9.]+% \(EditLens Llama-3\.2-3B\)\.",
    f"By conference 2026 the percentage of abstracts above threshold ranges from {yearly[2026]['pct_d']:.1f}% (desklib academic) to {yearly[2026]['pct_l']:.1f}% (EditLens Llama-3.2-3B).",
    text,
)
print(f"[OK] Updated Table 2 caption sentence")

# ---- Update Inter-Detector Convergence section ----
conv_old = re.search(
    r"Cohen's κ on binary classifications is [0-9.]+ \(desklib vs EditLens RoBERTa-large\), [0-9.]+ \(desklib vs EditLens Llama-3\.2-3B\), and [0-9.]+ \(EditLens RoBERTa-large vs Llama-3\.2-3B\)\. Pearson correlations between continuous scores are [0-9.]+, [0-9.]+, and [0-9.]+ for the three pairs",
    text,
)
if conv_old:
    new_conv = (f"Cohen's κ on binary classifications is {k['desklib_acad_vs_editlens_r']:.2f} "
                f"(desklib academic vs EditLens RoBERTa-large), "
                f"{k['desklib_acad_vs_editlens_l']:.2f} (desklib academic vs EditLens "
                f"Llama-3.2-3B), and {k['editlens_r_vs_l']:.2f} (EditLens RoBERTa-large "
                f"vs Llama-3.2-3B). Pearson correlations between continuous scores are "
                f"{rr['desklib_acad_vs_editlens_r']:.2f}, {rr['desklib_acad_vs_editlens_l']:.2f}, "
                f"and {rr['editlens_r_vs_l']:.2f} for the three pairs")
    text = text.replace(conv_old.group(0), new_conv)
    print(f"[OK] Updated Inter-Detector Convergence section")
else:
    print(f"[WARN] convergence pattern not matched")

# ---- H1 paragraph: pairwise kappa range ----
# Find "Pairwise Cohen's κ on binary classifications across detectors is X to Y"
kappa_min = min(k.values())
kappa_max = max(k.values())
text = re.sub(
    r"Pairwise Cohen's κ on binary classifications across detectors is [0-9.]+ to [0-9.]+\.",
    f"Pairwise Cohen's κ on binary classifications across detectors is {kappa_min:.2f} to {kappa_max:.2f}.",
    text,
)
print(f"[OK] Updated H1 pairwise kappa range")

# ---- Replace "desklib substitute" → "academic-tuned desklib" ----
text = text.replace("the desklib substitute", "the academic-tuned desklib detector")
text = text.replace("desklib substitute", "academic-tuned desklib detector")
print(f"[OK] Replaced 'desklib substitute' phrasing")

# ---- Update "53.8% (desklib)" mentions in Discussion ----
# In the Magnitude paragraph: "rose from a stable 5% to 27–64% in 2025 and 54–83% in 2026"
# These ranges depend on the per-cycle rates. Recompute.
y26 = yearly[2026]
y25 = yearly[2025]
mn26, mx26 = min(y26['pct_e'], y26['pct_l'], y26['pct_d']), max(y26['pct_e'], y26['pct_l'], y26['pct_d'])
mn25, mx25 = min(y25['pct_e'], y25['pct_l'], y25['pct_d']), max(y25['pct_e'], y25['pct_l'], y25['pct_d'])
text = re.sub(
    r"rose from a stable 5% to [0-9]+–[0-9]+% in 2025 and [0-9]+–[0-9]+% in 2026",
    f"rose from a stable 5% to {round(mn25)}–{round(mx25)}% in 2025 and {round(mn26)}–{round(mx26)}% in 2026",
    text,
)
print(f"[OK] Updated Discussion magnitude range")

# ---- Discussion "Exact Finding" 2026 range ----
text = re.sub(
    r"ranges from [0-9]+% to [0-9]+% depending on the detector, with the primary detector \(EditLens RoBERTa-large\) returning [0-9.]+%\.",
    f"ranges from {round(mn26)}% to {round(mx26)}% depending on the detector, with the primary detector (EditLens RoBERTa-large) returning {y26['pct_e']:.1f}%.",
    text,
)
print(f"[OK] Updated Exact Finding range")

# ---- Save ----
MD.write_text(text)
print(f"\nSaved -> {MD}")
print("\nNew P95 thresholds:")
print(f"  EditLens R single  = {P95_e:.4f}")
print(f"  EditLens R multi   = {P95_emw:.4f}")
print(f"  EditLens Llama     = {P95_l:.4f}")
print(f"  desklib academic   = {P95_d:.4f}")
print("\nH1 steps (95% CI):")
print(f"  EditLens R    : {h1_e['level_pp']:+.1f} pp [{h1_e['ci95_lo_pp']:+.1f}, {h1_e['ci95_hi_pp']:+.1f}]")
print(f"  EditLens Llama: {h1_l['level_pp']:+.1f} pp [{h1_l['ci95_lo_pp']:+.1f}, {h1_l['ci95_hi_pp']:+.1f}]")
print(f"  desklib acad  : {h1_d['level_pp']:+.1f} pp [{h1_d['ci95_lo_pp']:+.1f}, {h1_d['ci95_hi_pp']:+.1f}]")
