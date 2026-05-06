#!/usr/bin/env python3
"""
Academic Abstract Readability Analyzer

Analyzes academic abstracts for readability and writing quality,
detecting jargon overuse, nominalization, vague claims, and lack of specificity.

Usage:
    Single abstract:  python abstract_analyzer.py --text "Your abstract here..."
    From file:        python abstract_analyzer.py --file abstract.txt
    Batch CSV:        python abstract_analyzer.py --batch abstracts.csv --output results.json
    
CSV should have an 'abstract' column. JSON should be array of objects with 'abstract' field.
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
    
    # Split on sentence boundaries
    sentences = re.split(r'[.!?]+\s+', text)
    
    # Restore periods
    sentences = [s.replace('<PERIOD>', '.').strip() for s in sentences if s.strip()]
    
    return sentences


def tokenize_words(text: str) -> list[str]:
    """Extract words from text."""
    # Remove punctuation and split
    words = re.findall(r"\b[a-zA-Z]+(?:[-'][a-zA-Z]+)*\b", text.lower())
    return words


def is_complex_word(word: str) -> bool:
    """Check if word is complex (3+ syllables, excluding common suffixes)."""
    syllables = count_syllables(word)
    if syllables < 3:
        return False
    
    # Don't count as complex if complexity comes from common suffixes
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
    
    # Flesch Reading Ease
    fre = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    
    # Flesch-Kincaid Grade Level
    fk_grade = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    
    # Gunning Fog Index
    fog = 0.4 * ((num_words / num_sentences) + 100 * (num_complex / num_words))
    
    # SMOG Index (extrapolated for short texts)
    if num_sentences >= 30:
        smog = 1.043 * math.sqrt(num_polysyllables * (30 / num_sentences)) + 3.1291
    else:
        smog = 1.043 * math.sqrt(num_polysyllables * (30 / num_sentences)) + 3.1291
    
    # Automated Readability Index
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
        
        # Skip exclusions
        if word_lower in NOMINALIZATION_EXCLUSIONS:
            continue
        
        # Check suffixes
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
        # Simple heuristic: be verb followed by past participle pattern
        if re.search(be_verbs, sentence_lower) and re.search(past_participle, sentence_lower):
            # Check if they appear in order
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
    """Find jargon terms in text."""
    text_lower = text.lower()
    found = []
    
    # Check multi-word phrases first
    for term in MANAGEMENT_JARGON:
        if " " in term:  # Multi-word phrase
            if term in text_lower:
                found.append(term)
    
    # Check single words
    words = tokenize_words(text)
    for word in words:
        if word in MANAGEMENT_JARGON:
            found.append(word)
    
    return found


def detect_hedges(text: str) -> list[str]:
    """Find hedging language in text."""
    text_lower = text.lower()
    found = []
    
    # Check phrases first
    for hedge in HEDGES:
        if " " in hedge:  # Multi-word phrase
            if hedge in text_lower:
                found.append(hedge)
    
    # Check single words
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
    
    # Find numbers and statistics
    numbers = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?%?\b', text)
    indicators["numbers"] = numbers
    
    # Statistical notation
    stats = re.findall(r'\b[pnNrβ]\s*[=<>]\s*[\d.]+', text)
    stats += re.findall(r'\bp\s*[<>=]\s*\.?\d+', text_lower)
    indicators["statistics"] = stats
    
    # Methods mentioned
    for method in SPECIFIC_METHODS:
        if method in text_lower:
            indicators["methods"].append(method)
    
    # Sample indicators
    sample_patterns = [
        r'\bn\s*=\s*\d+', r'\bN\s*=\s*\d+',
        r'\d+\s*participants', r'\d+\s*respondents',
        r'\d+\s*firms', r'\d+\s*companies',
        r'\d+\s*observations', r'\d+\s*interviews',
    ]
    for pattern in sample_patterns:
        matches = re.findall(pattern, text_lower)
        indicators["sample_indicators"].extend(matches)
    
    # Theoretical markers (for theory papers)
    for marker in THEORETICAL_MARKERS:
        if marker in text_lower:
            indicators["theoretical_markers"].append(marker)
    
    # Vague quantifiers (negative)
    for vague in VAGUE_QUANTIFIERS:
        if vague in text_lower:
            indicators["vague_quantifiers"].append(vague)
    
    # Calculate score - empirical and theoretical indicators both count
    positive_points = (
        len(indicators["numbers"]) * 2 +
        len(indicators["statistics"]) * 3 +
        len(indicators["methods"]) * 2 +
        len(indicators["sample_indicators"]) * 3 +
        len(indicators["theoretical_markers"]) * 2  # Theory markers count too
    )
    
    negative_points = len(indicators["vague_quantifiers"]) * 1
    
    # Normalize to 0-1 (assuming max reasonable score around 20)
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
# COMPOSITE SCORING
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
    # Academic abstracts typically have FK grade 12-18; only penalize extremes
    # Old formula penalized grade 14 heavily; new formula treats 12-16 as acceptable
    fk_grade = traditional["flesch_kincaid_grade"]
    if fk_grade <= 12:
        fk_normalized = 100
    elif fk_grade <= 16:
        # Gentle slope: grade 12-16 maps to 100-70
        fk_normalized = 100 - (fk_grade - 12) * 7.5
    elif fk_grade <= 20:
        # Steeper slope: grade 16-20 maps to 70-40
        fk_normalized = 70 - (fk_grade - 16) * 7.5
    else:
        # Very steep: grade 20+ maps to 40-0
        fk_normalized = max(0, 40 - (fk_grade - 20) * 8)
    
    # Flesch Reading Ease - also recalibrate for academic norms
    # Academic writing typically scores 20-40; treat 30+ as acceptable
    fre = traditional["flesch_reading_ease"]
    if fre >= 50:
        fre_normalized = 100
    elif fre >= 30:
        # 30-50 maps to 70-100
        fre_normalized = 70 + (fre - 30) * 1.5
    elif fre >= 10:
        # 10-30 maps to 40-70
        fre_normalized = 40 + (fre - 10) * 1.5
    else:
        # Below 10 maps to 0-40
        fre_normalized = max(0, 40 + fre * 4)
    
    surface_readability = (fk_normalized + fre_normalized) / 2
    
    # Academic clarity (0-100) - unchanged
    nominalization_penalty = min(50, nom_density * 15)
    passive_penalty = min(20, passive_ratio * 30)
    jargon_penalty = min(30, jargon_density * 8)
    hedge_penalty = min(20, hedge_density * 12)
    specificity_bonus = specificity * 30
    
    academic_clarity = max(0, 100 - nominalization_penalty - passive_penalty 
                          - jargon_penalty - hedge_penalty + specificity_bonus)
    
    # Overall quality - REDUCED SURFACE WEIGHT
    # Academic clarity is what distinguishes good from bad academic writing
    # Surface readability matters less (complex ≠ bad)
    overall_quality = (surface_readability * 0.15) + (academic_clarity * 0.85)
    
    return {
        "surface_readability": round(surface_readability, 1),
        "academic_clarity": round(academic_clarity, 1),
        "overall_quality": round(overall_quality, 1),
    }


def generate_flags(
    nom_density: float,
    passive_ratio: float,
    jargon_density: float,
    hedge_density: float,
    specificity: float,
    nominalizations: list[str],
    jargon: list[str],
    hedges: list[str],
) -> list[dict]:
    """Generate flagged issues with severity."""
    flags = []
    
    # Nominalization flags
    if nom_density > 1.5:
        severity = "high" if nom_density > 2.5 else "medium"
        flags.append({
            "issue_type": "excessive_nominalization",
            "severity": severity,
            "value": round(nom_density, 2),
            "threshold": "1.5 per sentence",
            "examples": list(set(nominalizations))[:5],
        })
    
    # Passive voice flags
    if passive_ratio > 0.3:
        severity = "high" if passive_ratio > 0.5 else "medium"
        flags.append({
            "issue_type": "excessive_passive_voice",
            "severity": severity,
            "value": f"{round(passive_ratio * 100, 1)}%",
            "threshold": "30%",
            "examples": [],
        })
    
    # Jargon flags
    if jargon_density > 2:
        severity = "high" if jargon_density > 5 else "medium"
        flags.append({
            "issue_type": "excessive_jargon",
            "severity": severity,
            "value": round(jargon_density, 2),
            "threshold": "2%",
            "examples": list(set(jargon))[:5],
        })
    
    # Hedge flags
    if hedge_density > 1.0:
        severity = "high" if hedge_density > 2.0 else "medium"
        flags.append({
            "issue_type": "excessive_hedging",
            "severity": severity,
            "value": round(hedge_density, 2),
            "threshold": "1.0 per sentence",
            "examples": list(set(hedges))[:5],
        })
    
    # Low specificity flags
    if specificity < 0.2:
        severity = "high" if specificity < 0.1 else "medium"
        flags.append({
            "issue_type": "low_specificity",
            "severity": severity,
            "value": round(specificity, 2),
            "threshold": "0.2",
            "examples": ["No specific methods, sample sizes, or statistics found"],
        })
    
    return flags


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_abstract(text: str) -> dict:
    """Analyze a single abstract and return comprehensive metrics."""
    
    # Basic stats
    text_stats = calculate_text_stats(text)
    sentences = tokenize_sentences(text)
    words = tokenize_words(text)
    num_sentences = max(1, len(sentences))
    num_words = max(1, len(words))
    
    # Traditional readability
    traditional = calculate_traditional_readability(text)
    
    # Nominalization analysis
    nominalizations = detect_nominalizations(text)
    nom_density = len(nominalizations) / num_sentences
    nom_ratio = len(nominalizations) / num_words
    
    # Passive voice
    passive_flags = detect_passive_voice(sentences)
    passive_ratio = sum(passive_flags) / num_sentences
    
    # Jargon
    jargon = detect_jargon(text)
    jargon_density = (len(jargon) / num_words) * 100
    
    # Hedges
    hedges = detect_hedges(text)
    hedge_density = len(hedges) / num_sentences
    
    # Specificity
    specificity, specificity_breakdown = calculate_specificity(text)
    
    # Sentence variance
    sentence_variance = calculate_sentence_variance(sentences)
    
    # Composite scores
    composite = calculate_composite_scores(
        traditional, nom_density, passive_ratio, 
        jargon_density, hedge_density, specificity
    )
    
    # Flags
    flags = generate_flags(
        nom_density, passive_ratio, jargon_density, hedge_density,
        specificity, nominalizations, jargon, hedges
    )
    
    return {
        "text_stats": text_stats,
        "traditional_readability": traditional,
        "academic_quality_metrics": {
            "nominalization_density": round(nom_density, 3),
            "nominalization_ratio": round(nom_ratio, 4),
            "passive_voice_ratio": round(passive_ratio, 3),
            "jargon_density": round(jargon_density, 2),
            "hedge_density": round(hedge_density, 3),
            "specificity_score": round(specificity, 3),
            "sentence_complexity_variance": round(sentence_variance, 2),
        },
        "detected_items": {
            "nominalizations": list(set(nominalizations)),
            "jargon": list(set(jargon)),
            "hedges": list(set(hedges)),
            "specificity_indicators": specificity_breakdown,
        },
        "flagged_issues": flags,
        "composite_scores": composite,
    }


def analyze_batch(filepath: str) -> list[dict]:
    """Analyze multiple abstracts from CSV or JSON file."""
    path = Path(filepath)
    abstracts = []
    
    if path.suffix.lower() == '.csv':
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'abstract' in row:
                    abstracts.append(row['abstract'])
    elif path.suffix.lower() == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        abstracts.append(item)
                    elif isinstance(item, dict) and 'abstract' in item:
                        abstracts.append(item['abstract'])
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")
    
    results = []
    for i, abstract in enumerate(abstracts):
        result = analyze_abstract(abstract)
        result["_index"] = i
        results.append(result)
    
    return results


def generate_report(analysis: dict, abstract_preview: str = "") -> str:
    """Generate a human-readable report from analysis."""
    lines = []
    lines.append("=" * 60)
    lines.append("ACADEMIC ABSTRACT READABILITY ANALYSIS")
    lines.append("=" * 60)
    
    if abstract_preview:
        preview = abstract_preview[:200] + "..." if len(abstract_preview) > 200 else abstract_preview
        lines.append(f"\nText preview: {preview}\n")
    
    # Composite scores
    c = analysis["composite_scores"]
    lines.append(f"\n📊 COMPOSITE SCORES")
    lines.append(f"   Overall Quality:     {c['overall_quality']}/100")
    lines.append(f"   Surface Readability: {c['surface_readability']}/100")
    lines.append(f"   Academic Clarity:    {c['academic_clarity']}/100")
    
    # Traditional metrics
    t = analysis["traditional_readability"]
    lines.append(f"\n📖 TRADITIONAL READABILITY")
    lines.append(f"   Flesch Reading Ease:  {t['flesch_reading_ease']} (higher = easier)")
    lines.append(f"   Flesch-Kincaid Grade: {t['flesch_kincaid_grade']}")
    lines.append(f"   Gunning Fog Index:    {t['gunning_fog_index']}")
    
    # Academic quality
    a = analysis["academic_quality_metrics"]
    lines.append(f"\n🔬 ACADEMIC QUALITY METRICS")
    lines.append(f"   Nominalization density: {a['nominalization_density']:.2f} per sentence")
    lines.append(f"   Passive voice ratio:    {a['passive_voice_ratio']:.1%}")
    lines.append(f"   Jargon density:         {a['jargon_density']:.1f}%")
    lines.append(f"   Hedge density:          {a['hedge_density']:.2f} per sentence")
    lines.append(f"   Specificity score:      {a['specificity_score']:.2f}")
    
    # Flagged issues
    if analysis["flagged_issues"]:
        lines.append(f"\n⚠️  FLAGGED ISSUES")
        for flag in analysis["flagged_issues"]:
            severity_icon = "🔴" if flag["severity"] == "high" else "🟡"
            lines.append(f"   {severity_icon} {flag['issue_type']}: {flag['value']} (threshold: {flag['threshold']})")
            if flag["examples"]:
                examples = ", ".join(flag["examples"][:3])
                lines.append(f"      Examples: {examples}")
    else:
        lines.append(f"\n✅ No major issues flagged")
    
    lines.append("\n" + "=" * 60)
    
    return "\n".join(lines)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze academic abstracts for readability and writing quality"
    )
    parser.add_argument("--text", "-t", type=str, help="Abstract text to analyze")
    parser.add_argument("--file", "-f", type=str, help="File containing single abstract")
    parser.add_argument("--batch", "-b", type=str, help="CSV/JSON file with multiple abstracts")
    parser.add_argument("--output", "-o", type=str, help="Output file for results (JSON)")
    parser.add_argument("--report", "-r", action="store_true", help="Print human-readable report")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.batch:
        results = analyze_batch(args.batch)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to {args.output}")
        else:
            print(json.dumps(results, indent=2))
    
    elif args.text or args.file:
        if args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = args.text
        
        result = analyze_abstract(text)
        
        if args.json:
            print(json.dumps(result, indent=2))
        elif args.report or not args.json:
            print(generate_report(result, text))
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
                print(f"\nJSON results also saved to {args.output}")
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()