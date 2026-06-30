import re
from collections import Counter

from .config import (
    ADJACENT_TERMS,
    CONSULTING_COMPANIES,
    CORE_RETRIEVAL_TERMS,
    EVALUATION_TERMS,
    LEADERSHIP_TERMS,
    MUST_HAVE_TERMS,
    NEGATIVE_TERMS,
    NON_TARGET_AI_SIGNALS,
    PRODUCT_OWNERSHIP_TERMS,
    PRODUCT_SIGNALS,
    PRODUCTION_TERMS,
    PURE_RESEARCH_SIGNALS,
)


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#./-]*")
STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}
ROLE_PATTERNS = (
    re.compile(r"(?:job description|role|title)\s*:\s*([^\n|]+)", re.IGNORECASE),
    re.compile(r"^#*\s*([^#\n]{4,80})", re.IGNORECASE),
)
KNOWN_LOCATIONS = (
    "pune",
    "noida",
    "delhi",
    "delhi ncr",
    "gurgaon",
    "gurugram",
    "mumbai",
    "hyderabad",
    "bangalore",
    "bengaluru",
    "chennai",
    "kolkata",
    "remote",
    "india",
)


def _norm(value):
    return " ".join(str(value or "").lower().split())


def _tokenize(text):
    return [token for token in TOKEN_PATTERN.findall(_norm(text)) if token not in STOPWORDS]


def _matched_weighted_terms(jd_text, weighted_terms):
    normalized = _norm(jd_text)
    return {
        term: weight
        for term, weight in weighted_terms.items()
        if term in normalized
    }


def _matched_terms(jd_text, terms):
    normalized = _norm(jd_text)
    return {term for term in terms if term in normalized}


def _infer_role(jd_text):
    for pattern in ROLE_PATTERNS:
        match = pattern.search(jd_text.strip())
        if match:
            role = match.group(1).strip(" -*|")
            if role:
                return role[:90]
    return "Custom Role"


def _infer_experience(jd_text):
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:[-–—]|to)\s*(\d+(?:\.\d+)?)\s*\+?\s*years?",
        jd_text,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1)), float(match.group(2))
    match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", jd_text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        return max(value - 1, 0), value + 2
    return 0.0, 99.0


def _infer_locations(jd_text):
    normalized = _norm(jd_text)
    return tuple(location for location in KNOWN_LOCATIONS if location in normalized)


def _inferred_weighted_terms(jd_text, limit=28):
    tokens = _tokenize(jd_text)
    counts = Counter(tokens)
    inferred = {}
    for token, count in counts.most_common(limit):
        if len(token) >= 3 and not token.isdigit():
            inferred[token] = min(0.35 + 0.05 * count, 0.75)

    bigrams = Counter(
        f"{left} {right}"
        for left, right in zip(tokens, tokens[1:])
        if len(left) >= 3 and len(right) >= 3
    )
    for phrase, count in bigrams.most_common(12):
        inferred[phrase] = min(0.45 + 0.08 * count, 0.85)
    return inferred


def _target_title_terms(role):
    normalized = _norm(role)
    terms = {normalized} if normalized else set()
    role_words = [
        token
        for token in _tokenize(normalized)
        if token not in {"senior", "lead", "staff", "principal", "founding"}
    ]
    if role_words:
        terms.add(" ".join(role_words))
    return {term for term in terms if term}


def _default_jd_understanding():
    """Structured, reproducible interpretation of the JD before candidates are ranked."""
    return {
        "source": "default",
        "role": "Senior AI Engineer - Founding Team",
        "company_context": {
            "stage": "Series A",
            "team_shape": "founding AI engineering org",
            "product": "AI-native talent intelligence platform",
            "work_mode": "scrappy product engineering with deep ML systems ownership",
        },
        "core_mandate": (
            "Own candidate-JD matching, retrieval, ranking, and evaluation systems "
            "that recruiters and candidates use in production."
        ),
        "ideal_profile": {
            "experience_years": "roughly 5-9, with 6-8 strongest",
            "experience_min": 5.0,
            "experience_max": 9.0,
            "target_title_terms": HANDS_ON_TITLE_TERMS,
            "role_shape": "hands-on senior IC who still writes production code",
            "background": "applied ML/AI at product companies, not research-only or services-only",
            "proof": "shipped at least one end-to-end search, retrieval, ranking, recommendation, or matching system",
            "working_style": "early-stage, product-minded, willing to ship and iterate from user feedback",
        },
        "must_have_evidence": {
            "technical_terms": MUST_HAVE_TERMS,
            "retrieval_ranking_terms": CORE_RETRIEVAL_TERMS,
            "evaluation_terms": EVALUATION_TERMS,
            "production_terms": PRODUCTION_TERMS,
        },
        "strong_positive_evidence": {
            "product_ownership_terms": PRODUCT_OWNERSHIP_TERMS | PRODUCT_SIGNALS,
            "leadership_terms": LEADERSHIP_TERMS,
            "adjacent_terms": ADJACENT_TERMS,
        },
        "logistics": {
            "preferred_locations": ("pune", "noida", "delhi ncr", "mumbai", "hyderabad"),
            "notice_period": "sub-30 days strongest; 30-60 still acceptable with stronger fit",
            "availability": "active, responsive, open-to-work candidates are more actionable",
        },
        "negative_evidence": {
            "non_target_titles": NEGATIVE_TERMS,
            "consulting_only_companies": CONSULTING_COMPANIES,
            "research_without_shipping": PURE_RESEARCH_SIGNALS,
            "non_target_ai_domains": NON_TARGET_AI_SIGNALS,
            "anti_patterns": (
                "keyword stuffing without delivery evidence",
                "LangChain/OpenAI demos under 12 months without older production ML",
                "architecture-only seniority without recent hands-on production code",
                "title-chasing with very short tenures",
            ),
        },
    }


def _custom_jd_understanding(jd_text):
    role = _infer_role(jd_text)
    exp_min, exp_max = _infer_experience(jd_text)
    known_must = _matched_weighted_terms(jd_text, MUST_HAVE_TERMS)
    adjacent = _matched_weighted_terms(jd_text, ADJACENT_TERMS)
    inferred_terms = _inferred_weighted_terms(jd_text)
    technical_terms = {**inferred_terms, **known_must}
    retrieval_terms = _matched_terms(jd_text, CORE_RETRIEVAL_TERMS)
    evaluation_terms = _matched_terms(jd_text, EVALUATION_TERMS)
    production_terms = _matched_terms(jd_text, PRODUCTION_TERMS)
    product_terms = _matched_terms(jd_text, PRODUCT_OWNERSHIP_TERMS | PRODUCT_SIGNALS)
    leadership_terms = _matched_terms(jd_text, LEADERSHIP_TERMS)

    if not retrieval_terms:
        retrieval_terms = set(list(technical_terms)[:10])

    return {
        "source": "custom",
        "role": role,
        "company_context": {
            "stage": "custom JD",
            "team_shape": "parsed from user-provided JD",
            "product": "custom role context",
            "work_mode": "rank candidates against the uploaded JD",
        },
        "core_mandate": (
            "Rank candidates against the uploaded JD using extracted requirements, "
            "skills, role context, logistics, and negative signals."
        ),
        "ideal_profile": {
            "experience_years": (
                f"roughly {exp_min:g}-{exp_max:g} years"
                if exp_max < 99
                else "not explicitly constrained"
            ),
            "experience_min": exp_min,
            "experience_max": exp_max,
            "target_title_terms": _target_title_terms(role),
            "role_shape": role,
            "background": "candidate background should align with the uploaded JD",
            "proof": "candidate should show direct evidence for the JD's extracted responsibilities and skills",
            "working_style": "fit is inferred from JD language and candidate evidence",
        },
        "must_have_evidence": {
            "technical_terms": technical_terms,
            "retrieval_ranking_terms": retrieval_terms,
            "evaluation_terms": evaluation_terms,
            "production_terms": production_terms,
        },
        "strong_positive_evidence": {
            "product_ownership_terms": product_terms,
            "leadership_terms": leadership_terms,
            "adjacent_terms": adjacent,
        },
        "logistics": {
            "preferred_locations": _infer_locations(jd_text),
            "notice_period": "prefer faster availability when the JD implies urgency",
            "availability": "active, responsive, open-to-work candidates are more actionable",
        },
        "negative_evidence": {
            "non_target_titles": _matched_terms(jd_text, NEGATIVE_TERMS),
            "consulting_only_companies": _matched_terms(jd_text, CONSULTING_COMPANIES),
            "research_without_shipping": _matched_terms(jd_text, PURE_RESEARCH_SIGNALS),
            "non_target_ai_domains": _matched_terms(jd_text, NON_TARGET_AI_SIGNALS),
            "anti_patterns": (
                "keyword stuffing without delivery evidence",
                "candidate evidence that is unrelated to the uploaded JD",
            ),
        },
    }


def build_jd_understanding(jd_text=None):
    if jd_text and jd_text.strip():
        return _custom_jd_understanding(jd_text)
    return _default_jd_understanding()


def jd_retrieval_terms(jd_profile):
    """Flatten the JD profile into weighted retrieval phrases for precompute."""
    weights = {}
    weights.update(jd_profile["must_have_evidence"]["technical_terms"])
    weights.update(
        {
            term: weight * 0.55
            for term, weight in jd_profile["strong_positive_evidence"]["adjacent_terms"].items()
        }
    )
    for term in jd_profile["must_have_evidence"]["retrieval_ranking_terms"]:
        weights[term] = max(weights.get(term, 0.0), 1.25)
    for term in jd_profile["must_have_evidence"]["evaluation_terms"]:
        weights[term] = max(weights.get(term, 0.0), 1.05)
    for term in jd_profile["must_have_evidence"]["production_terms"]:
        weights[term] = max(weights.get(term, 0.0), 0.95)
    for term in jd_profile["strong_positive_evidence"]["product_ownership_terms"]:
        weights[term] = max(weights.get(term, 0.0), 0.7)
    for term in jd_profile["strong_positive_evidence"]["leadership_terms"]:
        weights[term] = max(weights.get(term, 0.0), 0.45)
    return weights
