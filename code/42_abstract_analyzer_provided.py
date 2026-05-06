#!/usr/bin/env python3
"""
Academic Abstract Readability Analyzer
PROVIDED BY USER ON 2026-05-04 — original source unknown.

This file is the user's provided analyzer. The pasted message was truncated
mid-function inside calculate_composite_scores() at "surface_read"; the
remainder of that function and any following code are missing.

Per user instruction: "implement this except the business specific jargon
measures" — the MANAGEMENT_JARGON dictionary and detect_jargon() function are
preserved here for reference but are NOT used in the SSWR analysis.

Analyzes academic abstracts for readability and writing quality,
detecting jargon overuse, nominalization, vague claims, and lack of
specificity.

Usage:
    Single abstract:  python abstract_analyzer.py --text "Your abstract here..."
    From file:        python abstract_analyzer.py --file abstract.txt
    Batch CSV:        python abstract_analyzer.py --batch abstracts.csv --output results.json

CSV should have an 'abstract' column. JSON should be array of objects with
'abstract' field.
"""

import argparse
import csv
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Optional

# =============================================================================
# DICTIONARIES
# =============================================================================

# NOTE: This jargon list is business/management-specific and per user
# instruction is NOT applied to the SSWR (social work) corpus. The list is
# preserved here for reference only.
MANAGEMENT_JARGON = {
    # Strategy buzzwords
    "synergy", "synergies", "leverage", "leveraging", "leveraged",
    "orchestration", "orchestrate", "orchestrating", "holistic", "holistically",
    "paradigm", "paradigmatic", "paradigms", "ecosystem", "ecosystems",
    "value-add", "value-added", "best practice", "best practices",
    "core competency", "core competencies", "competitive advantage",
    "strategic alignment", "alignment", "aligned",
    "stakeholder", "stakeholders", "stakeholder engagement",
    "bandwidth", "circle back", "deep dive", "drill down",
    "move the needle", "low-hanging fruit", "game-changer",
    "disrupt", "disruptive", "disruption",
    "scalable", "scalability", "agile", "pivot", "pivoting",
    "optimize", "optimization", "maximize", "maximization",
    "utilize", "utilization", "facilitate", "facilitation",
    "operationalize", "operationalization", "incentivize", "incentivization",
    "synergize", "strategize", "ideate", "ideation",
    "actionable", "impactful", "robust", "rigorous",
    "cutting-edge", "state-of-the-art", "world-class", "best-in-class",
    "mission-critical", "value proposition",
    "deliverable", "deliverables",
    "going forward", "at the end of the day", "touch base",
    "proactive", "proactively", "dynamic", "dynamically",
    "empower", "empowering", "empowerment",
    "transformative", "transformation", "transformational",
    "innovative", "innovation", "innovate",

    # Academic filler phrases
    "in terms of", "with respect to", "in the context of",
    "it is important to note", "it should be noted",
    "the fact that", "due to the fact that",
    "in order to", "for the purpose of",
    "a number of", "a variety of", "a range of",
    "plays a role", "plays an important role",
    "has an impact", "has a significant impact",
    "serves as", "serves to", "contributes to",
    "is related to", "are related to",
    "framework", "frameworks", "conceptual framework",
    "interplay", "nexus", "interface",
    "lens", "through the lens of",
    "unpack", "unpacking", "problematize", "problematizing",
    "situate", "situated", "situating",
}

HEDGES = {
    # Modal hedges
    "may", "might", "could", "would", "should",
    "possibly", "probably", "perhaps", "presumably",
    "potentially", "conceivably", "seemingly", "apparently",

    # Approximators
    "somewhat", "relatively", "fairly", "rather",
    "approximately", "roughly", "about", "around",
    "almost", "nearly", "virtually", "practically",

    # Epistemic phrases (matched as substrings)
    "it seems", "it appears", "it is possible",
    "it is likely", "it is probable", "it is plausible",
    "to some extent", "to a certain degree",
    "in some cases", "in certain circumstances",
    "tends to", "tend to", "appears to", "seems to",

    # Shield phrases
    "we believe", "we suggest", "we propose",
    "we argue", "we contend", "it can be argued",
    "one might argue", "it could be said",
    "generally", "typically", "usually", "often",
    "in general", "on the whole", "by and large",
}

# Nominalization suffixes to detect
NOMINALIZATION_SUFFIXES = (
    "tion", "sion", "ment", "ness", "ity", "ance", "ence", "acy", "ism", "ization"
)

# Common words to exclude from nominalization detection
NOMINALIZATION_EXCLUSIONS = {
    "nation", "nations", "station", "stations", "position", "positions",
    "question", "questions", "mention", "mentions", "attention",
    "section", "sections", "function", "functions", "action", "actions",
    "condition", "conditions", "addition", "tradition", "traditions",
    "competition", "portion", "portions", "emotion", "emotions",
    "fashion", "passion", "mission", "vision", "version", "versions",
    "tension", "pension", "mansion", "session", "sessions",
    "impression", "expression", "permission", "admission",
    "occasion", "occasions", "invasion", "division", "divisions",
    "decision", "decisions", "television", "revision",
    "government", "governments", "department", "departments",
    "management", "moment", "moments", "comment", "comments",
    "agreement", "agreements", "statement", "statements",
    "treatment", "environment", "environments", "element", "elements",
    "argument", "arguments", "document", "documents", "instrument", "instruments",
    "apartment", "basement", "equipment", "investment", "investments",
    "judgment", "payment", "payments", "movement", "movements",
    "business", "witness", "fitness", "illness", "awareness",
    "happiness", "darkness", "kindness", "weakness", "sadness",
    "city", "cities", "university", "universities", "community", "communities",
    "opportunity", "opportunities", "ability", "abilities", "quality", "qualities",
    "reality", "activity", "activities", "society", "societies",
    "majority", "minority", "authority", "authorities", "security",
    "identity", "property", "properties", "variety", "varieties",
    "quantity", "quantities", "personality", "priority", "priorities",
    "possibility", "possibilities", "responsibility", "responsibilities",
    "performance", "performances", "importance", "instance", "instances",
    "distance", "distances", "balance", "substance", "substances",
    "assistance", "resistance", "insurance", "alliance", "compliance",
    "experience", "experiences", "difference", "differences",
    "presence", "absence", "sentence", "sentences", "reference", "references",
    "conference", "conferences", "evidence", "science", "sciences",
    "influence", "audience", "audiences", "violence", "patience",
    "consequence", "consequences", "intelligence", "excellence",
    "democracy", "accuracy", "privacy", "legacy", "advocacy",
    "capitalism", "socialism", "journalism", "criticism", "terrorism",
    "mechanism", "mechanisms", "organism", "organisms", "tourism",
}

# Specificity indicators
SPECIFIC_METHODS = {
    "regression", "anova", "manova", "ancova", "t-test", "chi-square",
    "correlation", "factor analysis", "structural equation", "sem",
    "grounded theory", "ethnography", "ethnographic", "case study",
    "interview", "interviews", "survey", "surveys", "questionnaire",
    "experiment", "experimental", "quasi-experimental", "rct",
    "randomized controlled", "longitudinal", "cross-sectional",
    "meta-analysis", "systematic review", "content analysis",
    "discourse analysis", "thematic analysis", "phenomenological",
    "panel data", "fixed effects", "random effects", "diff-in-diff",
    "difference-in-differences", "instrumental variable", "propensity score",
    "multilevel", "hierarchical linear", "hlm", "mixed methods",
}

VAGUE_QUANTIFIERS = {
    "some", "many", "few", "several", "various", "numerous",
    "a lot", "a great deal", "a significant amount",
    "considerable", "substantial", "extensive",
}

# Theoretical paper indicators (for non-empirical specificity)
THEORETICAL_MARKERS = {
    "model", "models", "modeling",
    "equilibrium", "equilibria",
    "proposition", "propositions",
    "theorem", "theorems", "lemma", "lemmas", "corollary",
    "proof", "prove", "proves", "proven",
    "we show", "we derive", "we demonstrate",
    "closed-form", "analytical solution", "analytic solution",
    "steady state", "steady-state",
    "optimization", "maximization problem", "minimization problem",
    "first-order condition", "foc",
    "comparative statics", "comparative static",
    "nash equilibrium", "pareto", "welfare",
    "utility function", "production function", "cost function",
    "agent", "agents", "principal",
    "game", "games", "game-theoretic",
    "mechanism", "mechanism design",
    "endogenous", "exogenous",
    "derives from", "follows from", "implies that",
}

# =============================================================================
# TEXT PROCESSING UTILITIES
# =============================================================================

def count_syllables(word: str) -> int:
    """Count syllables in a word using a heuristic approach."""
    word = word.lower().strip()
    if not word:
        return 0

    # Handle common exceptions
    if len(word) <= 2:
        return 1

    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel

    # Adjust for silent e
    if word.endswith("e") and count > 1:
        count -= 1

    # Adjust for -le endings
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1

    # Ensure at least one syllable
    return max(1, count)


def tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Handle common abbreviations
    text = re.sub(r'\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|i\.e|e\.g)\.\s', r'\1<PERIOD> ', text)
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s.replace('<PERIOD>', '.').strip() for s in sentences if s.strip()]
    return sentences


def tokenize_words(text: str) -> list[str]:
    """Extract words from text."""
    words = re.findall(r"\b[a-zA-Z]+(?:[-'][a-zA-Z]+)*\b", text.lower())
    return words


def is_complex_word(word: str) -> bool:
    """Check if word is complex (3+ syllables, excluding common suffixes)."""
    syllables = count_syllables(word)
    if syllables < 3:
        return False

    word_lower = word.lower()
    if word_lower.endswith(("es", "ed", "ing", "ly")):
        base = re.sub(r"(es|ed|ing|ly)$", "", word_lower)
        if count_syllables(base) < 3:
            return False

    return True


# =============================================================================
# METRIC CALCULATIONS
# =============================================================================

def calculate_text_stats(text: str) -> dict:
    """Calculate basic text statistics."""
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)

    if not words or not sentences:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "avg_sentence_length": 0.0,
            "avg_word_length_chars": 0.0,
            "avg_syllables_per_word": 0.0,
        }

    total_syllables = sum(count_syllables(w) for w in words)
    total_chars = sum(len(w) for w in words)

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_length": len(words) / len(sentences),
        "avg_word_length_chars": total_chars / len(words),
        "avg_syllables_per_word": total_syllables / len(words),
    }


def calculate_traditional_readability(text: str) -> dict:
    """Calculate standard readability metrics."""
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)

    if not words or not sentences:
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade": 0.0,
            "gunning_fog_index": 0.0,
            "smog_index": 0.0,
            "automated_readability_index": 0.0,
        }

    num_sentences = len(sentences)
    num_words = len(words)
    num_syllables = sum(count_syllables(w) for w in words)
    num_chars = sum(len(w) for w in words)
    num_complex = sum(1 for w in words if is_complex_word(w))
    num_polysyllables = sum(1 for w in words if count_syllables(w) >= 3)

    fre = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    fk_grade = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    fog = 0.4 * ((num_words / num_sentences) + 100 * (num_complex / num_words))
    if num_sentences >= 30:
        smog = 1.043 * math.sqrt(num_polysyllables * (30 / num_sentences)) + 3.1291
    else:
        smog = 1.043 * math.sqrt(num_polysyllables * (30 / num_sentences)) + 3.1291
    ari = 4.71 * (num_chars / num_words) + 0.5 * (num_words / num_sentences) - 21.43

    return {
        "flesch_reading_ease": round(fre, 2),
        "flesch_kincaid_grade": round(fk_grade, 2),
        "gunning_fog_index": round(fog, 2),
        "smog_index": round(smog, 2),
        "automated_readability_index": round(ari, 2),
    }


def detect_nominalizations(text: str) -> list[str]:
    """Find nominalization instances in text."""
    words = tokenize_words(text)
    found = []
    for word in words:
        word_lower = word.lower()
        if word_lower in NOMINALIZATION_EXCLUSIONS:
            continue
        if word_lower.endswith(NOMINALIZATION_SUFFIXES) and len(word_lower) > 5:
            found.append(word_lower)
    return found


def detect_passive_voice(sentences: list[str]) -> list[bool]:
    """Detect passive voice in each sentence."""
    be_verbs = r"\b(is|are|was|were|been|being|be|am)\b"
    past_participle = r"\b\w+(ed|en|t)\b"
    results = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if re.search(be_verbs, sentence_lower) and re.search(past_participle, sentence_lower):
            be_match = re.search(be_verbs, sentence_lower)
            pp_match = re.search(past_participle, sentence_lower)
            if be_match and pp_match and be_match.end() < pp_match.start():
                results.append(True)
            else:
                results.append(False)
        else:
            results.append(False)
    return results


def detect_jargon(text: str) -> list[str]:
    """Find jargon terms in text. NOT USED in SSWR analysis (business-specific)."""
    text_lower = text.lower()
    found = []
    for term in MANAGEMENT_JARGON:
        if " " in term:
            if term in text_lower:
                found.append(term)
    words = tokenize_words(text)
    for word in words:
        if word in MANAGEMENT_JARGON:
            found.append(word)
    return found


def detect_hedges(text: str) -> list[str]:
    """Find hedging language in text."""
    text_lower = text.lower()
    found = []
    for hedge in HEDGES:
        if " " in hedge:
            if hedge in text_lower:
                found.append(hedge)
    words = tokenize_words(text)
    for word in words:
        if word in HEDGES and " " not in word:
            found.append(word)
    return found


def calculate_specificity(text: str) -> tuple[float, dict]:
    """Calculate specificity score and breakdown."""
    text_lower = text.lower()
    words = tokenize_words(text)

    indicators = {
        "numbers": [],
        "statistics": [],
        "methods": [],
        "sample_indicators": [],
        "theoretical_markers": [],
        "vague_quantifiers": [],
    }

    numbers = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?%?\b', text)
    indicators["numbers"] = numbers

    stats = re.findall(r'\b[pnNrβ]\s*[=<>]\s*[\d.]+', text)
    stats += re.findall(r'\bp\s*[<>=]\s*\.?\d+', text_lower)
    indicators["statistics"] = stats

    for method in SPECIFIC_METHODS:
        if method in text_lower:
            indicators["methods"].append(method)

    sample_patterns = [
        r'\bn\s*=\s*\d+', r'\bN\s*=\s*\d+',
        r'\d+\s*participants', r'\d+\s*respondents',
        r'\d+\s*firms', r'\d+\s*companies',
        r'\d+\s*observations', r'\d+\s*interviews',
    ]
    for pattern in sample_patterns:
        matches = re.findall(pattern, text_lower)
        indicators["sample_indicators"].extend(matches)

    for marker in THEORETICAL_MARKERS:
        if marker in text_lower:
            indicators["theoretical_markers"].append(marker)

    for vague in VAGUE_QUANTIFIERS:
        if vague in text_lower:
            indicators["vague_quantifiers"].append(vague)

    positive_points = (
        len(indicators["numbers"]) * 2 +
        len(indicators["statistics"]) * 3 +
        len(indicators["methods"]) * 2 +
        len(indicators["sample_indicators"]) * 3 +
        len(indicators["theoretical_markers"]) * 2
    )

    negative_points = len(indicators["vague_quantifiers"]) * 1

    raw_score = positive_points - negative_points
    normalized = max(0, min(1, raw_score / 20))

    return normalized, indicators


def calculate_sentence_variance(sentences: list[str]) -> float:
    """Calculate standard deviation of sentence lengths."""
    if len(sentences) < 2:
        return 0.0
    lengths = [len(tokenize_words(s)) for s in sentences]
    return statistics.stdev(lengths)


# =============================================================================
# COMPOSITE SCORING  ── TRUNCATED IN USER PASTE; needs the rest of the file ──
# =============================================================================

def calculate_composite_scores(
    traditional: dict,
    nom_density: float,
    passive_ratio: float,
    jargon_density: float,
    hedge_density: float,
    specificity: float
) -> dict:
    """Calculate composite quality scores."""

    # Surface readability - RECALIBRATED FOR ACADEMIC WRITING
    fk_grade = traditional["flesch_kincaid_grade"]
    if fk_grade <= 12:
        fk_normalized = 100
    elif fk_grade <= 16:
        fk_normalized = 100 - (fk_grade - 12) * 7.5
    elif fk_grade <= 20:
        fk_normalized = 70 - (fk_grade - 16) * 7.5
    else:
        fk_normalized = max(0, 40 - (fk_grade - 20) * 8)

    fre = traditional["flesch_reading_ease"]
    if fre >= 50:
        fre_normalized = 100
    elif fre >= 30:
        fre_normalized = 70 + (fre - 30) * 1.5
    elif fre >= 10:
        fre_normalized = 40 + (fre - 10) * 1.5
    else:
        fre_normalized = max(0, 40 + fre * 4)

    # surface_read[ability] = ... <— USER PASTE ENDED HERE.
    # The rest of calculate_composite_scores() and any code that follows is
    # missing. Returning a stub so the file still imports cleanly.
    raise NotImplementedError(
        "calculate_composite_scores is incomplete — the user paste was "
        "truncated mid-function. Need the remaining body and any "
        "subsequent code (CLI runner, batch processing, output formatting)."
    )
