import re
from functools import lru_cache


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def norm_text(value):
    if value is None:
        return ""
    return str(value).lower()


@lru_cache(maxsize=512)
def phrase_pattern(phrase):
    return re.compile(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])")


def phrase_present(text, phrase):
    """Whole-phrase match so short signals like 'ml' do not match 'html'."""
    phrase = norm_text(phrase).strip()
    if not phrase:
        return False

    # Most evidence phrases are distinctive enough for direct substring checks.
    # Boundary regex is reserved for short ambiguous tokens where false positives
    # are common, e.g. "ml" inside "html".
    if len(phrase) <= 3 and re.search(r"^[a-z0-9]+$", phrase):
        return phrase_pattern(phrase).search(text) is not None

    return phrase in text


def contains_any(text, terms):
    return any(phrase_present(text, term) for term in terms)


def count_weighted_terms(text, weighted_terms):
    score = 0.0
    hits = []
    for term, weight in weighted_terms.items():
        if phrase_present(text, term):
            score += weight
            hits.append(term)
    return score, hits
