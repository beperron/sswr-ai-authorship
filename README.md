# SSWR AI-Authorship Detection

Reproducibility package for *Population-level detection of AI-assisted authorship
in social work conference abstracts: A time-series analysis of the Society for
Social Work and Research, 2010–2026.*

**Author** Brian E. Perron, University of Michigan School of Social Work
· [beperron@umich.edu](mailto:beperron@umich.edu)
· ORCID [0000-0001-5840-0908](https://orcid.org/0000-0001-5840-0908)

---

## Overview

Pre-registered analysis of generative-AI stylistic signatures in *N* = 21,569
SSWR conference abstracts (conference years 2010–2026), scored by three
open-weight detectors and a Gartenberg-aligned writing-quality battery.
Percentile-anchored *P*₉₅ thresholds are locked on a 2010–2017 baseline
prior to inspection of any post-2017 score distribution.

| Detector                            | no-exposure 2010–2023 | full-exposure 2025–2026 | step at conf 2025                |
|:------------------------------------|----------------------:|------------------------:|:---------------------------------|
| EditLens RoBERTa-large *(primary)*  |               5–14 %  |          32 % → 56 %    | **+17.5 pp**, 95 % CI [+14.0, +21.1] |
| EditLens Llama-3.2-3B               |              ≤ 32 %   |          64 % → 83 %    | +29.1 pp, 95 % CI [+18.4, +39.7]    |
| desklib academic-tuned              |               5–10 %  |          32 % → 59 %    | +21.1 pp, 95 % CI [+18.1, +24.2]    |

All three detectors converge on direction, timing, and approximate magnitude
of the post-2024 step. Pairwise Cohen's κ ≈ 0.41.

---

## Repository layout

```
.
├── gartenberg.py                      Gartenberg writing-quality reference code
│                                      (provided by S. Hasan; checksum below)
├── code/                              analysis pipeline, numbered execution order
├── results/                           authoritative JSON outputs
│   └── figures/                       manuscript figures (PNG @ 300 DPI + SVG)
├── checkpoints/                       locked P95 thresholds (timestamped)
└── logs/                              protocol-deviation log + per-run audit JSON
```

The corpus, detector-score pickles, the HuggingFace model cache, and the
manuscript itself are not redistributed in this repository. See **Data** below.

---

## Data

The corpus is released separately as the **SSWR History Database**
(Perron et al., in press). To reproduce the analysis, download the two CSV
files and place them in `data/`:

- `sswr_papers.csv` — abstract text + metadata
- `sswr_paper_authors.csv` — canonical author IDs

> Data source: *<!-- TODO: insert SSWR History Database URL -->*

Detector-score pickle files are **not** redistributable per the
pre-registration ethics statement; reviewers regenerate them locally by
running the scoring scripts on the corpus.

The analysis is population-level and cannot identify individual authors as
having used AI assistance. Inclusion criteria: scientific-format abstracts,
conference years 2010–2026, ≥ 100 words, non-empty text, no within-year
duplicates. *N* = 21,569.

---

## Reproduction

```bash
git clone https://github.com/beperron/sswr-ai-authorship && cd sswr-ai-authorship

uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install torch transformers peft pandas numpy scipy statsmodels \
               matplotlib tqdm scikit-learn ruptures textstat spacy
python -m spacy download en_core_web_sm

# Place sswr_papers.csv and sswr_paper_authors.csv in data/ (see above)
```

Accept the model-license terms on HuggingFace for the four gated checkpoints
and save a token at `~/.cache/huggingface/token`:

- `pangram/editlens_roberta-large`
- `pangram/editlens_Llama-3.2-3B`
- `meta-llama/Llama-3.2-3B` *(base for the Llama variant)*
- `desklib/ai-text-detector-academic-v1.01`

Run the pipeline in numbered order. Each script is idempotent given the
locked thresholds in `checkpoints/`.

| Stage              | Scripts |
|:-------------------|:--------|
| Corpus prep        | `01_inspect_filter.py` · `02_preprocess.py` · `02b_attach_first_author.py` |
| Detector scoring   | `19_score_editlens_roberta.py` · `20_score_editlens_llama.py` · `26_score_editlens_roberta_multiwindow.py` · `46_score_desklib_academic.py` |
| Writing quality    | `45_run_hassan_on_corpus.py` *(primary; runs `gartenberg.py`)* · `25_writing_quality.py` *(textstat robustness check)* |
| Sensitivity        | `07_changepoint.py` · `09_qual_vs_quant.py` · `09b_fa_rank.py` · `11_robustness.py` · `13_esl_country_stratification.py` · `14_length_control.py` · `16_bootstrap.py` |
| Main analysis      | `47_main_analysis.py` |
| Figures            | `39_regenerate_figures_2010.py` |

The pipeline is deterministic given identical model-checkpoint hashes
(recorded in `logs/19_*.json`, `logs/20_*.json`, `logs/26_*.json`,
`logs/46_*.json`).

---

## Provenance — `gartenberg.py`

`gartenberg.py` is the reference Python implementation of the writing-quality
battery from Gartenberg, Hasan, Murray, & Pierce (2026), *More versus better:
Artificial intelligence, incentives, and the emerging crisis in peer review*,
Organization Science. The file was supplied directly by **Saerom Hasan**
(second author) and is included **byte-identical** to the version received.

```bash
shasum -a 256 gartenberg.py
# cae8c08a2d798bf01d3b122aa3a06a07755a36803f76a1871cb6a472510e885c

diff gartenberg.py code/44_hassan_analyzer.py     # no output → byte-identical
```

The duplicate at `code/44_hassan_analyzer.py` is referenced by file path in
the manuscript and is kept synchronized with the root copy.

---

## Traceability

Every numeric claim in the manuscript maps to one result file in `results/`.

| Manuscript element                                  | Result file |
|:----------------------------------------------------|:------------|
| H1 — yearly proportions, ITS step, κ, Pearson *r*   | `main_analysis_results.json` |
| H2 — DiD by faculty rank                            | `h2_rank_h3_qual_did_2010_2017_calibration.json` |
| H3 — DiD by methodology (qual vs quant)             | `h2_rank_h3_qual_did_2010_2017_calibration.json` |
| H4 — within-baseline year coefficient               | `h4_within_baseline_drift_2010_2017.json` |
| Country exploratory DiD                             | `country_did_2010_2017_calibration.json` |
| Prior-submissions cohort (Gartenberg-aligned)       | `prior_submissions_analysis.json` |
| Writing-quality ITS (Table 5)                       | `writing_quality_its_hassan.json` |
| Writing-quality cross-pipeline correlation          | `hassan_vs_existing_comparison.json` |
| Sensitivity — block-bootstrap CI                    | `bootstrap_its.json` |
| Sensitivity — log-word-count covariate              | `length_control.json` |
| Sensitivity — blinded changepoint                   | `changepoint_results.json` |
| Sensitivity — robustness battery                    | `robustness.json` |
| Figures 1–3                                         | `figures/*.{png,svg}` |

---

## Pre-registration

`logs/PROTOCOL_DEVIATIONS.md` is an append-only record of every departure
from the pre-registered design, dated and rationale-attached.
`checkpoints/calibration_editlens_locked.json` and
`calibration_editlens_llama_locked.json` are the timestamped *P*₉₅ thresholds
written before any post-2017 score distribution was inspected.

---

## Citation

```
Perron, B. E. (2026). Population-level detection of AI-assisted authorship in
social work conference abstracts: A time-series analysis of the Society for
Social Work and Research, 2010–2026 [Manuscript]. University of Michigan
School of Social Work.
```

Downstream replications using the writing-quality reference code should
additionally cite:

```
Gartenberg, C., Hasan, S., Murray, A., & Pierce, L. (2026). More versus
better: Artificial intelligence, incentives, and the emerging crisis in peer
review. Organization Science. https://doi.org/10.1287/orsc.2026.ed.v37.n3
```

and credit the reference-code provision to S. Hasan.

---

Issues, replication failures, or corrections — open a GitHub issue or email
[beperron@umich.edu](mailto:beperron@umich.edu).
