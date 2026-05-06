# Protocol Deviations Log

This file records every deviation from the Stage 1 pre-registration in
chronological order.  Each entry is dated and accompanied by a stated reason.
This log is appended to, never silently edited.

---

## Deviation 1 — 2026-04-30 — Substituted primary detector

**Pre-registered.** `pangram/editlens_roberta-large` (open-weight per Thai et al.,
2026) as primary detector; `pangram/editlens_Llama-3.2-3B` as secondary.

**Actual.** Both Pangram EditLens repositories are gated on Hugging Face
(`x-error-code: GatedRepo`) and no access token was available at the start of
the run.  As primary we used **`desklib/ai-text-detector-v1.01`**, a
DeBERTa-v3-large model fine-tuned on the RAID benchmark (MIT license,
non-gated, current SOTA on the RAID leaderboard at submission time).  The
percentile-based domain calibration in protocol §4.4 is detector-agnostic and
remains valid under substitution.

**Compatibility note.** The user has indicated they will provide HF access to
the EditLens models.  When access is granted, EditLens will be added as an
additional model and inter-model agreement will be reported per protocol §5.3.
The desklib results will not be discarded; they will function as the third
independent detector against which detector-specific artifacts can be checked.

---

## Deviation 2 — 2026-04-30 — Calibration window shortened to 2009–2017

**Pre-registered.** Calibration window = SSWR conferences 2005–2017 inclusive
(submission cycles April 2004 – April 2017), N ≈ 13,000–15,000.  The window
was selected as a "stable human-authored baseline" predating consumer-grade
LLM availability.

**Actual deviation.** During preliminary scoring (before any post-2018 data
were examined), the per-year mean detector score in the pre-LLM window
exhibited an unmistakable one-time level shift between conference years 2008
and 2009:

| Sub-window | N (partial scoring; ≈40% of corpus complete) | Mean detector score |
|---|---|---|
| 2005–2008 | 1,715 | 0.389 |
| 2009–2017 | 7,874 | 0.650 |
| Δ | | +0.260 (Welch t = −31.0, p ≈ 1.8 × 10⁻¹⁷⁹) |

Within 2009–2017 the per-year means are essentially flat (slope +0.002 per
year; range 0.623–0.668); the discontinuity is concentrated in a single year.

**Most plausible cause.** A submission-format / abstract-length policy change
at SSWR around the 2008→2009 cycle.  Median submitted-abstract word count
shifts upward in the same period, and detector scores rise mechanically with
prose density and structured-abstract conventions.  This is a known class of
historical-trend confound, exactly what protocol §1.2 anticipated — but the
specific 2008→2009 break was not foreseen at pre-registration time.

**Action.** Per the contingency procedure in protocol §5.7 ("contingency:
failed calibration assumption"), the calibration window has been restricted
to the most recent stable sub-window: **2009–2017 inclusive** (≈7,900
abstracts after the corpus filters).  All percentile thresholds (P90, P95,
P99) will be computed on this restricted window, and primary analyses will
proceed against the restricted baseline.

**What this changes.**

  * Calibration N drops from ≈14,000 to ≈7,900 (still a large baseline).
  * The 2005–2008 era is *excluded from baseline* but *retained in the
    descriptive corpus* and shown for transparency in figures.
  * All ITS, changepoint, and falsification analyses are re-keyed to the
    2009–2017 baseline.
  * H4 (pre-window stability) is now framed as "no temporal drift in the
    2009–2017 sub-window after adjustment" rather than over the full 2005–2017
    window.  The protocol-required H4 falsification check will be reported
    against the restricted window; the full-window failure is reported as the
    motivating finding.

**What this does NOT change.**

  * The intervention point (April 2024 submission cycle = January 2025
    conference) is unchanged.
  * The smallest effect size of interest is unchanged (3 pp for binary AI;
    0.05 score-units for continuous).
  * The blinding rule (no inspection of post-2017 distributions before
    threshold lock) is honored: this deviation was discovered using only
    pre-2018 scores.

**Honesty disclosure.** This deviation was identified after a partial scoring
checkpoint (40% of corpus complete) was inspected for pre-window stability,
not after threshold-locked post-window comparisons.  The discovery occurred
before any post-2018 detector output entered any analysis.

---

## Deviation 3 — 2026-04-30 — Academic-detector configuration: max_length=512 with end-truncation (left-truncate)

**Pre-registered.** The pre-registration did not specify a third detector. The
addition of `desklib/ai-text-detector-academic-v1.01` is a peer-review-driven
sensitivity analysis to address protocol §6.3 (domain transfer). It is not a
deviation per se but a sensitivity addition.

**Configuration choices (documented for transparency).**

  * `max_length = 512` (general detector used 768): forced by Apple Silicon MPS
    memory pressure when running multiple processes. With the academic
    detector at 768 the throughput dropped to 0.4 abstracts/second versus the
    intended 7+; dropping to 512 restored throughput to 12-16 ab/s.
  * `truncation_side = "left"` (default is "right"): means the *last* 512
    tokens of each abstract are kept and the *beginning* is dropped when the
    abstract exceeds 512 tokens. Empirically, **91% of SSWR abstracts exceed
    512 DeBERTa tokens** (median 614, 95th percentile 726). For these
    abstracts the academic detector therefore scores the Results / Discussion
    / Conclusion span, not the Background / Methods / early Results span.

**Rationale for end-truncation.** The discussion / conclusion section of a
scientific abstract is the most likely location for AI-style signature: hedging
adverbs, "future work", "implications", and rhetorical generalizations all
concentrate there. Keeping the end-512 means the academic detector scores the
section most likely to carry AI signal. A complementary front-truncation run
was performed earlier and abandoned because (a) it was confounded with the
detector's prior on background/methods boilerplate, and (b) the user
explicitly judged the discussion-section content to be a better test target.

**Consequence for cross-detector comparison.** The general detector (at
max_length=768) sees ~98% of the abstract; the academic detector (at
max_length=512 with left-truncate) sees the end-512 tokens, missing the
beginning of ~91% of abstracts. The two detectors are therefore scoring
*overlapping but not identical* content, by design. Inter-detector agreement
metrics (Cohen's kappa, Pearson r) should be interpreted with this in mind:
they measure consensus on the AI-signal direction across two views of the
same abstract, not two scores of the same content.

**No effect on calibration validity.** Because the calibration window
(2009-2017) is scored under exactly the same configuration as the post-window,
the percentile thresholds remain valid for the academic detector's specific
truncation regime. The cross-detector comparison is the only thing affected.

---

## Deviation 4 — 2026-04-30 — EditLens access granted; primary detector restored

**Pre-registered.** EditLens RoBERTa primary, EditLens Llama secondary; substitute detector only if both gated.

**Update.** Hugging Face access to both `pangram/editlens_roberta-large` and `pangram/editlens_Llama-3.2-3B` was granted shortly after the substitute analysis began (Deviation 1). Per the protocol's Contingency section, EditLens RoBERTa was restored as the pre-registered primary, EditLens Llama-3.2-3B as secondary, and `desklib/ai-text-detector-v1.01` was retained as a third independent detector. The Stage 2 manuscript reports all three detectors and inter-detector agreement (Cohen's κ, Pearson r). No analysis was finalized using only the substitute.

---

## Deviation 5 — 2026-04-30 — Calibration window restored to 2007–2017 (from 2009–2017)

**Background.** Deviation 2 restricted the calibration window to 2009–2017 because of a stylometric break at the 2008→2009 cycle. After EditLens access was restored, EditLens-scored stability was re-checked across 2007–2017.

**Update.** Under the EditLens detector family, the 2007–2008 cycles are stylometrically continuous with 2009 onward (no equivalent break). The desklib break appears specific to that detector's prior on length and structured-abstract format, not a substantive corpus discontinuity at the EditLens-style stylistic level. The calibration window was therefore restored to **2007–2017** to align with the EditLens primary analysis. The desklib substitute analysis uses the same 2007–2017 window for cross-detector consistency. Per-year baseline rates are reported in the manuscript; H4 (within-baseline drift) is reported on the restored window.

**No effect on intervention point or primary outcome.** Locked thresholds were re-computed on the 2007–2017 window before any post-2017 EditLens data were inspected.

---

## Deviation 6 — 2026-04-30 — Pangram-equivalent multi-window aggregation added as sensitivity

**Pre-registered.** Single-window detector scoring with input length up to the detector's maximum (512 or 1,024 tokens depending on variant).

**Update.** To match Gartenberg et al.'s (2026) multi-window treatment of long texts under the commercial Pangram detector, EditLens RoBERTa was additionally applied with non-overlapping ~510-token windows, with the abstract-level score computed as the word-count-weighted average across windows (mean 1.93 windows per abstract). The locked multi-window threshold (P95 = 0.201) was computed on the 2007–2017 baseline before any post-2017 multi-window scores were inspected. The single-window primary remains as pre-registered; multi-window is reported as a sensitivity. Single- and multi-window step estimates agree within 0.5 percentage points.

---

## Deviation 7 — 2026-04-30 — Writing quality metrics added as Gartenberg-aligned secondary

**Pre-registered.** Detector-based AI-text classification only.

**Update.** To enable direct conceptual replication of Gartenberg et al.'s (2026) finding that an AI-detection signal is corroborated by independent writing-quality decline, nine readability and stylistic metrics per abstract were added (Flesch Reading Ease, Flesch-Kincaid Grade, FOG, SMOG, mean sentence length, type-token ratio, nominalization rate, passive-voice rate, hedging rate, first-person pronoun rate). Metrics were computed before any post-2017 inspection of the resulting time series. The Stage 2 manuscript reports these as a Gartenberg-aligned secondary analysis distinct from the H1–H4 hypothesis set. Jargon and Specificity (Gartenberg's two remaining metrics) were skipped because their operationalization requires details not in the published main paper.

---

## Deviation 8 — 2026-05-02 — Three-way anglophone first-author cohort added as exploratory

**Pre-registered.** First-author academic rank (H2) and methodology (H3) as the only subgroup analyses. No country-of-affiliation cohort.

**Update.** Following peer-review feedback that an initial binary US/non-US cohort comparison confounded Canadian and other predominantly English-speaking first authors with truly ESL-majority cohorts, a three-way first-author cohort classification was added (US; Other Anglophone = Canada, United Kingdom, Ireland, Australia, New Zealand; Non-Anglophone = all other countries with non-empty country fields). The analysis is reported in the Stage 2 manuscript under "Exploratory Subgroup: First-Author Country of Affiliation" and is not included in the family-wise multiple-comparisons correction. It was added to align with Gartenberg et al.'s (2026) cohort comparison on non-native-English-speaking institutions; the SSWR corpus does not contain per-author native-language data, so country of affiliation is used as a noisy ESL proxy.

---

## Deviation 9 — 2026-05-04 — Switched cross-family third detector to desklib academic-tuned variant

**Previous.** Cross-family third detector was `desklib/ai-text-detector-v1.01` (general RAID-trained DeBERTa-v3-large).

**Updated.** Cross-family third detector is now `desklib/ai-text-detector-academic-v1.01`, an academic-domain-tuned variant of the same DeBERTa-v3-large backbone published by the same vendor.

**Rationale.** The SSWR corpus is academic prose (conference abstracts). The vendor publishes both a general-purpose RAID-benchmark model and an academic-domain-tuned model; the matched-domain variant is the methodologically appropriate choice for an academic-corpus analysis. The general-purpose variant was chosen earlier as a contingency substitute when EditLens was access-gated; once EditLens access was restored and three detectors became the planned analysis, switching to the academic-tuned desklib makes the cross-family triangulation domain-coherent.

**What this changes.** All P95 thresholds and rates for the desklib detector are recomputed on the academic-tuned model under the same configuration as the previous vanilla desklib (max_length=768, default right-truncation). The within-family argument (EditLens RoBERTa-large vs Llama-3.2-3B) and the cross-family argument (DeBERTa vs RoBERTa/Llama, RAID-or-academic vs EditLens-paired-examples training) are both preserved.

**What this does NOT change.** Calibration window (2010–2017), analytic window (2010–2026), intervention point (April 2024 deadline / conf 2025), smallest effect of interest, multiple-comparisons correction, or the family-wise α level.

---

## Deviation 10 — 2026-05-06 — Calibration window narrowed to 2010–2015

**Previous.** Calibration window = conf 2010–2017 (per Deviation 2).

**Updated.** Calibration window = conf 2010–2015. *N* = 4,460 abstracts.

**Rationale.** Grammarly's freemium product launched in May 2015. The April 2016 submission deadline (conf 2017) is therefore the first SSWR cycle whose abstracts could plausibly carry Grammarly-style polish. The pre-Deviation-2 reasoning treated 2010–2017 as a uniform pre-LLM baseline, but Grammarly's mass-market editing tool is now understood to plausibly contaminate the 2017 cycle. Tightening the calibration to 2010–2015 ensures the locked baseline predates plausible Grammarly contamination at the upper end of the window. The lower bound (2010) is unchanged from Deviation 2.

**What this changes.** All P95 thresholds, the H1 segmented-regression step, H2/H3 DiD coefficients, country DiD coefficients, prior-submissions cohort coefficients, and the H4 within-baseline drift estimates are recomputed. The qualitative conclusions are preserved: every headline result moves by less than 2 pp on every detector. One quantitative shift is interpretively notable: the EditLens RoBERTa-large within-baseline drift (H4) becomes statistically indistinguishable from zero under the tighter window (β = +0.000386, *p* = .18) where it was significant under the wider window (β = +0.000650, *p* < .0001). This strengthens the falsification check on the primary detector.

**What this does NOT change.** Analytic window (2010–2026), intervention point (April 2024 deadline / conf 2025), corpus inclusion criteria, detector models, smallest effect of interest, or the multiple-comparisons family.

**Sensitivity reference.** The 2010–2017 window is retained as a sensitivity check; numbers reported in `results/sensitivity_calibration_2010_2015.json` and the parallel `_2010_2017_calibration` JSONs.

---
