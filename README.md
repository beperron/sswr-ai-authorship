# SSWR AI-Authorship Detection

Reproducibility package for *Easier to Write, Harder to Read: AI-Assisted
Authorship and Writing-Quality Decline in Social Work Conference Abstracts*
(Perron, 2026).

**Author** Brian E. Perron, University of Michigan School of Social Work
· [beperron@umich.edu](mailto:beperron@umich.edu)
· ORCID [0000-0001-5840-0908](https://orcid.org/0000-0001-5840-0908)

---

## Overview

Population-level analysis of generative-AI stylistic signatures in *N* = 21,569
SSWR conference abstracts (conference years 2010–2026), scored by three
open-weight detectors and a Gartenberg-aligned writing-quality battery.
Percentile-anchored *P*₉₅ thresholds are computed on a conf 2010–2015
calibration window (*n* = 4,460), an upper bound that predates Grammarly's
May 2015 freemium launch and therefore the first SSWR cycle (conf 2017,
April 2016 submission deadline) whose abstracts could plausibly carry
consumer-grade machine-editing polish. The pre-Grammarly 2010–2015 window
is the headline calibration; the wider 2010–2017 window is reported as a
sensitivity check (every result moves by < 2 pp).

| Detector                            | no-exposure 2010–2023 | full-exposure 2025–2026 | step at conf 2025                |
|:------------------------------------|----------------------:|------------------------:|:---------------------------------|
| EditLens RoBERTa-large *(primary)*  |               5–15 %  |          33 % → 57 %    | **+17.8 pp**, 95 % CI [+14.3, +21.3] |
| EditLens Llama-3.2-3B               |              ≤ 37 %   |          66 % → 84 %    | +27.6 pp, 95 % CI [+16.8, +38.5]    |
| desklib academic-tuned              |                4–10 % |          31 % → 59 %    | +20.9 pp, 95 % CI [+18.0, +23.9]    |

All three detectors converge on direction, timing, and approximate magnitude
of the post-2024 step. Pairwise Cohen's κ ranges 0.38–0.41.

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

The corpus, detector-score pickles, the HuggingFace model cache, the
manuscript itself, and an `archive/` directory of superseded artifacts are
not redistributed in this repository. See **Data** below.

---

## Data

The corpus is released separately as the **SSWR History Database**
(Perron, Victor, & Qi, 2026). To reproduce the analysis, download the two
CSV files and place them in `data/`:

- `sswr_papers.csv` — abstract text + metadata
- `sswr_paper_authors.csv` — canonical author IDs

> Data source: *<!-- TODO: insert SSWR History Database URL -->*

Detector-score pickle files are **not** redistributable per the project's
ethics statement; reviewers regenerate them locally by running the scoring
scripts on the corpus.

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

Run the pipeline in numbered order. All scripts use repo-relative paths
(`Path(__file__).resolve().parent.parent`) and write into `data/`,
`results/`, `checkpoints/`, and `logs/` of this repository.

| Stage              | Scripts |
|:-------------------|:--------|
| Corpus prep        | `01_inspect_filter.py` · `02_preprocess.py` · `02b_attach_first_author.py` |
| Detector scoring   | `19_score_editlens_roberta.py` · `20_score_editlens_llama.py` · `26_score_editlens_roberta_multiwindow.py` · `46_score_desklib_academic.py` |
| Writing quality    | `45_run_hassan_on_corpus.py` *(primary; runs `gartenberg.py` via `44_hassan_analyzer.py`)* · `25_writing_quality.py` *(textstat reimplementation, robustness check)* |
| Sensitivity        | `07_changepoint.py` · `11_robustness.py` · `13_esl_country_stratification.py` · `14_length_control.py` · `16_bootstrap.py` |
| Main analysis      | `51_recalibrate_2010_2015_full.py` |
| Calibration-window sensitivity | `50_sensitivity_calibration_window.py` |
| First-time submitter rank composition | `55_first_time_submitter_ranks.py` |
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

| Manuscript element                                                          | Result file |
|:----------------------------------------------------------------------------|:------------|
| H1 — yearly above-P95 proportions, ITS step, Cohen's κ, Pearson *r*         | `main_analysis_results.json` |
| H2 — DiD by prior-submissions cohort (new entrants vs established)          | `prior_submissions_analysis.json` |
| H3 — DiD by first-author country cohort (US / Other-Anglophone / Non-Anglophone) | `country_did_2010_2015_calibration.json` |
| H4 — within-baseline year coefficient (calibration-drift falsification)     | `h4_within_baseline_drift_2010_2015.json` |
| Calibration-window sensitivity (2010–2015 vs 2010–2017)                     | `sensitivity_calibration_2010_2015.json` |
| First-time submitter rank composition                                       | `first_time_submitter_ranks.json` |
| Writing-quality FRE SD baseline (figure standardization)                    | `fre_baseline_2010_2015.json` |
| Table 4 — writing-quality ITS step                                          | `writing_quality_its_hassan.json` |
| Writing-quality cross-pipeline correlation                                  | `hassan_vs_existing_comparison.json` |
| Sensitivity — block-bootstrap CI                                            | `bootstrap_its.json` |
| Sensitivity — log-word-count covariate                                      | `length_control.json` |
| Sensitivity — blinded changepoint                                           | `changepoint_results.json` |
| Sensitivity — robustness battery                                            | `robustness.json` |
| Figures 1–3                                                                 | `figures/*.{png,svg}` |

`51_recalibrate_2010_2015_full.py` is the comprehensive main-analysis script
and writes the first six rows above plus `fre_baseline_2010_2015.json`.

---

## Pre-registration and protocol

The full study was developed iteratively rather than under a binding
pre-registration; `logs/PROTOCOL_DEVIATIONS.md` records analytic decisions
and revisions chronologically, including the calibration-window choice
(Deviation 10), detector-family selection (Deviations 1, 9), the conference-year
indexing scheme, and the addition of the country cohort comparison.
`checkpoints/calibration_editlens_locked.json` and
`calibration_editlens_llama_locked.json` are timestamped *P*₉₅ thresholds
saved at the time of scoring.

---

## Citation

```
Perron, B. E. (2026). Easier to write, harder to read: AI-assisted
authorship and writing-quality decline in social work conference abstracts
[Manuscript]. University of Michigan School of Social Work.
```

Downstream replications using the writing-quality reference code should
additionally cite:

```
Gartenberg, C., Hasan, S., Murray, A., & Pierce, L. (2026). More versus
better: Artificial intelligence, incentives, and the emerging crisis in
peer review. Organization Science. Advance online publication.
```

and credit the reference-code provision to S. Hasan.

---

Issues, replication failures, or corrections — open a GitHub issue or email
[beperron@umich.edu](mailto:beperron@umich.edu).
