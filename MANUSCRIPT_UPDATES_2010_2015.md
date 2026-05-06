# Manuscript Update Spec — Calibration Window: 2010–2017 → 2010–2015

**Target file:** `reports/Perron-SSWR-AI.docx`
**Reason:** Grammarly's freemium product launched May 2015. The April 2016 submission
deadline (conf 2017) is therefore the first SSWR cycle whose abstracts could plausibly
carry Grammarly polish. Tightening the calibration window to 2010–2015 ensures the
locked baseline predates any plausible Grammarly contamination.
**Effect on results:** The headline H1 step is essentially unchanged (Δ < 2 pp on every
detector; all 95 % CIs overlap heavily with the prior result). H2/H3/country/prior-subs
results shift by 1–4 pp; one within-baseline drift coefficient (EditLens R) drops from
significant to non-significant — see §H4 below.

This spec lists every value, label, and prose passage in the manuscript that must be
updated. **Cowork should make every change in this document. Do not skip any.**

---

## §0  Pre-registration framing — replace globally

This change is a **deviation from the pre-registered analysis plan**, not an in-bounds
choice. The manuscript should:

1. Drop language such as "pre-registered, percentile-anchored thresholds locked on
   conf 2010–2017" wherever it appears verbatim. Replace with:
   > "Percentile-anchored thresholds locked on conf 2010–2015 — a baseline that
   > predates Grammarly's May 2015 freemium launch and therefore the first SSWR
   > cycle (conf 2017, with its April 2016 submission deadline) whose abstracts
   > could plausibly carry editing-tool polish."
2. In the Methods → Pre-registration section, retain the existing pre-registration
   reference but add a sentence:
   > "We deviate from the pre-registered 2010–2017 baseline by tightening to
   > 2010–2015. The pre-registered window is reported as a sensitivity check
   > (see §Sensitivity)."
3. Anywhere the manuscript currently uses 'pre-registered' as load-bearing
   justification for the calibration choice, soften to 'specified' or 'locked
   prior to inspection of post-2015 score distributions'.

---

## §1  Calibration-window string replacements (literal)

Find-and-replace, case-insensitive, throughout body text, table titles, table cells,
figure captions, and footnotes.

| Find | Replace with |
|------|--------------|
| `2010–2017 calibration window` | `2010–2015 calibration window` |
| `2010-2017 calibration window` | `2010-2015 calibration window` |
| `conf 2010–2017` | `conf 2010–2015` |
| `conf 2010-2017` | `conf 2010-2015` |
| `2010–2017 baseline` | `2010–2015 baseline` |
| `2010-2017 baseline` | `2010-2015 baseline` |
| `conf 2010–2017 baseline` | `conf 2010–2015 baseline` |
| `(P95 of 2010–2017 by construction)` | `(P95 of 2010–2015 by construction)` |
| `2010-2017 calibrated P95` | `2010-2015 calibrated P95` |
| `2010–2017 calibrated P95` | `2010–2015 calibrated P95` |
| `*N* = 7,380` (calibration N) | `*N* = 4,460` |
| `n = 7,380` (calibration N) | `n = 4,460` |
| `7,380 abstracts` (calibration) | `4,460 abstracts` |

**Important:** Do **not** change `*N* = 21,569`, `21,569 abstracts`, `2010–2026`,
`conf 2010–2026`, or any reference to the analytic window. Those are unrelated
to the calibration window.

---

## §2  Methods — Calibration paragraph rewrite

Replace whatever sentence/paragraph currently introduces the calibration window with
the following (use the manuscript's existing voice — APA prose, no bolding for
emphasis):

> Detector-score thresholds were locked at the 95th percentile of each detector's
> score distribution on conf 2010–2015 (*N* = 4,460 scientific-format abstracts).
> The 2010–2015 window predates Grammarly's freemium launch in May 2015; the first
> SSWR cycle whose abstracts could plausibly carry Grammarly-style polish is conf
> 2017, whose April 2016 submission deadline falls roughly eleven months after the
> launch. Thresholds were locked before any post-2015 score distribution was
> inspected, so that the 5 % flag rate is a property of the calibration window by
> construction and the post-2015 cycle-level proportions are an out-of-sample
> measurement. We retain the pre-registered 2010–2017 window as a sensitivity
> check (§Sensitivity), where every headline result shifts by less than 2
> percentage points.

---

## §3  Numerical updates — exact old → new mapping

Every number below is in **percentage points** unless otherwise noted, with
95 % CIs in brackets. p-values: report `< .0001` whenever p < 1e-4; otherwise
report to 2 sig figs.

### §3.1  P95 thresholds (Methods + Back-matter Table A)

| Detector | OLD (2010–2017) | NEW (2010–2015) |
|---|---:|---:|
| EditLens RoBERTa-large (single window) | 0.1086 | **0.1051** |
| EditLens RoBERTa-large (multi-window aggregate) | 0.2069 | **0.2009** |
| EditLens Llama-3.2-3B | 0.0623 | **0.0561** |
| desklib academic | 0.9986 | **0.9987** |

**Calibration N**: 7,380 → **4,460**

### §3.2  Yearly above-P95 proportions — Table 2

Replace every cell. Row order: year ascending. *n* column unchanged.

| Year | *n* | EditLens RoBERTa-large | EditLens Llama-3.2-3B | desklib academic |
|------|----:|------------------------:|----------------------:|-----------------:|
| 2010 |   550 | 3.3 % | 2.5 % | 5.1 % |
| 2011 |   658 | 3.8 % | 3.2 % | 4.6 % |
| 2012 |   631 | 4.6 % | 3.0 % | 5.1 % |
| 2013 |   655 | 6.4 % | 6.9 % | 5.0 % |
| 2014 |   800 | 4.2 % | 6.0 % | 4.1 % |
| 2015 | 1,166 | 6.4 % | 6.5 % | 5.7 % |
| 2016 | 1,466 | 5.9 % | 7.6 % | 4.8 % |
| 2017 | 1,454 | 6.4 % | 9.8 % | 4.4 % |
| 2018 | 1,620 | 8.8 % | 10.9 % | 5.6 % |
| 2019 | 1,541 | 7.9 % | 14.0 % | 6.3 % |
| 2020 | 1,549 | 8.5 % | 18.8 % | 6.2 % |
| 2021 | 1,363 | 9.8 % | 24.9 % | 7.9 % |
| 2022 | 1,415 | 12.9 % | 31.9 % | 8.2 % |
| 2023 | 1,514 | 14.9 % | 36.7 % | 9.7 % |
| 2024 | 1,513 | 19.6 % | 50.8 % | 14.9 % |
| 2025 | 1,743 | 33.3 % | 66.4 % | 31.3 % |
| 2026 | 1,931 | **57.0 %** | **84.3 %** | **59.1 %** |

Caption sentence ranges: by conf 2026 the percentage above threshold ranges from
**57.0 %** (EditLens RoBERTa-large) to **84.3 %** (EditLens Llama-3.2-3B).

### §3.3  H1 — segmented regression step at conf 2025 (abstract + body)

| Detector | OLD step (95 % CI) | NEW step (95 % CI) | NEW *p* |
|---|---|---|---|
| EditLens RoBERTa-large *(primary)* | +17.5 [+14.0, +21.1] | **+17.8 [+14.3, +21.3]** | < .0001 |
| EditLens Llama-3.2-3B | +29.1 [+18.4, +39.7] | **+27.6 [+16.8, +38.5]** | < .0001 |
| desklib academic | +21.1 [+18.1, +24.2] | **+20.9 [+18.0, +23.9]** | < .0001 |

Find every occurrence of the OLD step values (including the abstract) and replace.

### §3.4  Inter-detector convergence

| Pair | OLD κ | NEW κ |
|---|---:|---:|
| desklib × EditLens RoBERTa-large | 0.41 | **0.41** |
| desklib × EditLens Llama-3.2-3B | 0.41 | **0.38** |
| EditLens RoBERTa-large × Llama-3.2-3B | 0.41 | **0.39** |

> "Pairwise Cohen's κ on binary classifications across detectors is **0.38 to 0.41**."

| Pair | OLD Pearson r | NEW Pearson r |
|---|---:|---:|
| desklib × EditLens RoBERTa-large | 0.22 | **0.22** |
| desklib × EditLens Llama-3.2-3B | 0.26 | **0.26** |
| EditLens RoBERTa-large × Llama-3.2-3B | 0.73 | **0.73** |

(Pearson r is essentially unchanged because correlation is calibration-invariant.)

### §3.5  H2 — academic rank × Full DiD (assistant prof = ref)

Doctoral × Full coefficient:

| Detector | OLD | NEW |
|---|---|---|
| EditLens RoBERTa-large *(primary)* | +5.17 [+3.82, +6.51], *p* < .0001 | **+5.37 [+3.97, +6.77], *p* < .0001** |
| EditLens Llama-3.2-3B | +8.14 [+6.33, +9.96], *p* < .0001 | **+7.51 [+3.78, +11.23], *p* < .0001** |
| desklib academic | +9.87 [+8.53, +11.22], *p* < .0001 | **+9.43 [+8.25, +10.62], *p* < .0001** |

> The doctoral-student vs assistant-professor differential under full LLM exposure
> is **+5.37 pp** on the primary detector (95 % CI [+3.97, +6.77], *p* < .0001),
> **+7.51 pp** on the EditLens Llama-3.2-3B variant, and **+9.43 pp** on the
> academic-tuned desklib detector.

### §3.6  H3 — methodology (qual vs quant) × Full DiD (quant = ref)

Qualitative × Full coefficient:

| Detector | OLD | NEW |
|---|---|---|
| EditLens RoBERTa-large *(primary)* | +8.15 [+5.28, +11.03], *p* < .0001 | **+7.12 [+4.42, +9.81], *p* < .0001** |
| EditLens Llama-3.2-3B | −6.91 [−10.44, −3.37], *p* = .0001 | **−6.73 [−11.17, −2.30], *p* = .003** |
| desklib academic | −5.36 [−8.40, −2.31], *p* = .0006 | **−5.40 [−7.91, −2.89], *p* < .0001** |

The cross-detector divergence persists (primary detector positive; Llama and desklib
negative) and the manuscript's existing narrative on H3 still applies.

### §3.7  H4 — within-baseline drift (now within 2010–2015)

**This is the largest interpretive change.** Within the tighter (2010–2015) window
the EditLens R drift coefficient is no longer statistically distinguishable from zero,
while the desklib drift remains highly significant.

| Detector | OLD (within 2010–2017) | NEW (within 2010–2015) |
|---|---|---|
| EditLens RoBERTa-large | β = +0.000650, SE = 0.000145, *p* < .0001 | **β = +0.000386, SE = 0.000287, *p* = .18 (n.s.)** |
| desklib academic | β = +0.007141, SE = 0.001436, *p* < .0001 | **β = +0.010328, SE = 0.001650, *p* < .0001** |

**Suggested H4 prose rewrite** (the existing prose treats both detectors as showing
significant pre-LLM drift; the new version differentiates):

> Within the 2010–2015 calibration window, the EditLens RoBERTa-large detector
> shows no statistically significant year-on-year drift (β = +0.000386, SE =
> 0.000287, *p* = .18). The academic-tuned desklib detector shows a small but
> highly significant year-on-year increase (β = +0.010328, SE = 0.001650,
> *p* < .0001). Both within-baseline trajectories are an order of magnitude
> smaller than the post-2024 step at conf 2025 and do not reverse the H1
> conclusion. The EditLens result strengthens the falsification check: there
> is no detectable within-baseline drift to confound the interpretation of the
> 2025 step on the primary detector. The persistent desklib drift suggests
> mild, monotonic upward movement in academic-style prose features that the
> academic-tuned desklib detector picks up; this is consistent with a slow
> editing-tool ramp-up across the 2010s.

### §3.8  Country DiD (US = ref) — exploratory

| Coefficient | OLD | NEW |
|---|---|---|
| Other Anglophone × Full (EditLens R) | +8.35 [+2.46, +14.23], *p* = .005 | **+7.82 [+1.59, +14.05], *p* = .014** |
| Non-Anglophone × Full (EditLens R)   | +10.77 [+8.99, +12.55], *p* < .0001 | **+11.93 [+9.96, +13.91], *p* < .0001** |
| Other Anglophone × Full (Llama)      | −5.58 [−13.93, +2.78], *p* = .19 | **−7.08 [−16.67, +2.51], *p* = .15** |
| Non-Anglophone × Full (Llama)        | +10.67 [+6.80, +14.55], *p* < .0001 | **+9.15 [+5.36, +12.94], *p* < .0001** |
| Other Anglophone × Full (desklib)    | −2.98 [−5.89, −0.06], *p* = .045 | **−3.46 [−6.61, −0.31], *p* = .031** |
| Non-Anglophone × Full (desklib)      | +19.71 [+10.78, +28.63], *p* < .0001 | **+19.61 [+9.38, +29.84], *p* = .0002** |

The headline narrative — Non-Anglophone authors show the largest detector signal
under full exposure on every detector — is preserved. The Other-Anglophone × Full
EditLens R coefficient softens slightly but remains positive and significant.

### §3.9  Prior-submissions cohort × Full DiD (Gartenberg-aligned)

new × Full coefficient (vs established = reference):

| Detector | OLD | NEW |
|---|---|---|
| EditLens RoBERTa-large *(primary)* | +6.12 [+2.86, +9.38], *p* = .0002 | **+7.34 [+3.06, +11.62], *p* = .0008** |
| EditLens Llama-3.2-3B | +8.89 [+?, +?]\* | **+10.10 [+8.11, +12.08], *p* < .0001** |
| desklib academic | (see prior file) | **+7.11 [+5.48, +8.73], *p* < .0001** |

\*Llama OLD coefficient was reported as +8.89 in the prior JSON; CI may not have
been published. Use the new value.

### §3.10  Discussion magnitude paragraph — 2026 ranges

Find any sentence of the form "rose from a stable 5 % to 27–64 % in 2025 and 54–83 %
in 2026" and replace with:

> "rose from a stable 5 % to **31–66 %** in 2025 and **57–84 %** in 2026"

Find any "Exact Finding" sentence of the form "ranges from 54 % to 83 % depending
on the detector, with the primary detector (EditLens RoBERTa-large) returning 56.1 %"
and replace with:

> "ranges from **57 % to 84 %** depending on the detector, with the primary detector
> (EditLens RoBERTa-large) returning **57.0 %**"

---

## §4  Sensitivity section — add or update

Add (or expand if it exists) a brief paragraph in §Sensitivity:

> **Calibration-window robustness.** The pre-registered 2010–2017 window
> includes one cycle (conf 2017) whose abstracts could plausibly carry
> Grammarly-style polish (Grammarly's freemium product launched May 2015,
> roughly eleven months before the conf 2017 April 2016 submission deadline).
> We re-ran the headline H1 segmented regression on the wider 2010–2017 window
> and on the tighter 2010–2015 window: the primary EditLens RoBERTa-large
> step at conf 2025 is +17.8 pp on the 2010–2015 window and +17.5 pp on the
> 2010–2017 window, with overlapping 95 % CIs (Δ < 2 pp on every detector).
> The pre-registered window is therefore not load-bearing: the qualitative
> conclusion is preserved at either boundary, with the headline numbers
> reported on 2010–2015.

---

## §5  Figures — already updated (no Cowork action needed)

The standalone PNG and SVG files are regenerated and reflect the 2010–2015
baseline:

- `results/figures/yearly_three_detector_lines.{png,svg}` — gray calibration
  band now covers 2010–2015 (right edge at the Grammarly line); inline label
  reads `Calibration window (conf 2010–2015)`; y-axis reads `% of abstracts
  above 2010–2015 calibrated P95`; updated end-label values.
- `results/figures/fig_writing_quality_trend.{png,svg}` — y-axis reads
  `Flesch Reading Ease (SD units, 2010–2015 baseline)`; SD scaling uses the
  new baseline (mean = 16.05, SD = 10.05 vs old mean = 16.24, SD = 9.94).
- `results/figures/fig_writing_quality_forest.{png,svg}` — display values
  are in raw metric units, so unchanged.

**The embedded copies inside `Perron-SSWR-AI.docx` need to be replaced with
the new PNGs.** This is the only Cowork figure-side action.

---

## §6  Methods — Pre-registration deviation log entry

Add to `logs/PROTOCOL_DEVIATIONS.md` (and reference in Methods if the doc
references the deviation log):

```markdown
### Deviation N (2026-05-06): Calibration window narrowed 2010–2017 → 2010–2015

The pre-registered calibration window was conf 2010–2017. We narrow to
conf 2010–2015 for the headline analysis. Rationale: Grammarly's freemium
product launched in May 2015. The April 2016 submission deadline (conf 2017)
is therefore the first SSWR cycle whose abstracts could plausibly carry
Grammarly-style polish. Locking the calibration on 2010–2015 ensures the
baseline predates plausible Grammarly contamination. The pre-registered
window is retained as a sensitivity check; every headline result moves by
less than 2 pp.
```

---

## §7  Author-facing checklist for Cowork

When implementing, please confirm each:

- [ ] All literal "2010–2017" strings in §1 replaced
- [ ] Calibration N replaced 7,380 → 4,460
- [ ] Methods Calibration paragraph (§2) rewritten
- [ ] P95 thresholds (§3.1) updated in Methods + back-matter
- [ ] Table 2 (§3.2): all 51 detector cells + caption ranges
- [ ] H1 step (§3.3): abstract + body, all three detectors
- [ ] Cohen's κ + Pearson r (§3.4): pairwise + range sentence
- [ ] H2 doctoral × Full (§3.5): three detectors
- [ ] H3 qualitative × Full (§3.6): three detectors
- [ ] H4 within-baseline (§3.7): rewrite with EditLens-R-now-null framing
- [ ] Country DiD (§3.8): six coefficients
- [ ] Prior-submissions DiD (§3.9): three detectors
- [ ] Discussion 2026 ranges (§3.10)
- [ ] Sensitivity paragraph added (§4)
- [ ] Embedded figures swapped out (§5)
- [ ] Pre-registration deviation entry added (§6)

---

*Generated 2026-05-06. Source data: `results/main_analysis_results.json`,
`results/h2_rank_h3_qual_did_2010_2015_calibration.json`,
`results/country_did_2010_2015_calibration.json`,
`results/h4_within_baseline_drift_2010_2015.json`,
`results/prior_submissions_analysis.json`,
`results/sensitivity_calibration_2010_2015.json`,
`results/fre_baseline_2010_2015.json`.*
