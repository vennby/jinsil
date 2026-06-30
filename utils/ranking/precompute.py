import math
import re
import time
from collections import Counter
from datetime import datetime, timezone

from .config import DEFAULT_PRECOMPUTE_PATH
from .features import candidate_text
from .io import iter_candidates, log_progress, write_precomputed_signals
from .jd_understanding import build_jd_understanding, jd_retrieval_terms
from .scoring import score_candidate
from .text import clamp


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#./-]*")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
FEATURE_NAMES = (
    "semantic_score",
    "technical",
    "career",
    "evidence_depth",
    "title",
    "seniority",
    "product",
    "engagement",
    "trust",
    "inverse_penalty",
    "core_coverage",
    "eval_coverage",
    "production_coverage",
)
FIXED_COVERAGE_WEIGHTS = {
    "semantic_score": 0.28,
    "technical": 0.12,
    "career": 0.06,
    "evidence_depth": 0.16,
    "title": 0.05,
    "seniority": 0.04,
    "product": 0.04,
    "engagement": 0.03,
    "trust": 0.02,
    "inverse_penalty": 0.07,
    "core_coverage": 0.08,
    "eval_coverage": 0.03,
    "production_coverage": 0.02,
}


def tokenize(text):
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS]


def query_weights(jd_profile):
    weights = Counter()
    for term, weight in jd_retrieval_terms(jd_profile).items():
        for token in tokenize(term):
            weights[token] = max(weights[token], weight)

    return dict(weights)


def document_stats(candidates_path, weights, progress_every=10000, quiet=False):
    doc_freq = Counter()
    total_length = 0
    candidate_count = 0
    started_at = time.perf_counter()
    query_tokens = set(weights)

    for candidate in iter_candidates(candidates_path):
        candidate_count += 1
        counts = Counter(tokenize(candidate_text(candidate)))
        total_length += sum(counts.values())
        for token in counts:
            if token in query_tokens:
                doc_freq[token] += 1

        if progress_every and candidate_count % progress_every == 0:
            elapsed = max(time.perf_counter() - started_at, 0.001)
            log_progress(
                (
                    f"Precompute pass 1: {candidate_count:,} candidates "
                    f"({candidate_count / elapsed:,.0f}/sec)"
                ),
                quiet,
            )

    avg_doc_length = total_length / max(candidate_count, 1)
    return candidate_count, avg_doc_length, doc_freq


def bm25_score(counts, doc_length, candidate_count, avg_doc_length, doc_freq, weights):
    k1 = 1.25
    b = 0.72
    score = 0.0
    length_norm = k1 * (1.0 - b + b * doc_length / max(avg_doc_length, 1.0))

    for token, query_weight in weights.items():
        frequency = counts.get(token, 0)
        if not frequency:
            continue

        idf = math.log(1.0 + (candidate_count - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5))
        saturation = (frequency * (k1 + 1.0)) / (frequency + length_norm)
        score += query_weight * idf * saturation

    return score


def feature_vector(row):
    components = row["components"]
    technical_details = components["technical_details"]
    return {
        "semantic_score": row["semantic_score"],
        "technical": components["technical"],
        "career": components["career"],
        "evidence_depth": components["evidence_depth"],
        "title": components["title"],
        "seniority": components["seniority"],
        "product": components["product"],
        "engagement": components["engagement"],
        "trust": components["trust"],
        "inverse_penalty": 1.0 - components["penalty"],
        "core_coverage": min(technical_details["core_signal_count"] / 4.0, 1.0),
        "eval_coverage": 1.0 if technical_details["eval_signal_count"] > 0 else 0.0,
        "production_coverage": (
            1.0 if technical_details["production_signal_count"] > 0 else 0.0
        ),
    }


def dot(weights, features):
    return sum(weights[name] * features[name] for name in FEATURE_NAMES)


def normalized_weights(weights):
    total = sum(max(value, 0.0) for value in weights.values()) or 1.0
    return {name: max(weights.get(name, 0.0), 0.0) / total for name in FEATURE_NAMES}


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (set, tuple)):
        return sorted(json_safe(item) for item in value)
    return value


def fixed_coverage_score(features):
    return clamp(dot(normalized_weights(FIXED_COVERAGE_WEIGHTS), features))


def compute_precompute_artifact(
    candidates_path,
    output_path=DEFAULT_PRECOMPUTE_PATH,
    artifact_limit=15000,
    progress_every=10000,
    quiet=False,
    jd_text=None,
    jd_profile=None,
):
    jd_profile = jd_profile or build_jd_understanding(jd_text)
    weights = query_weights(jd_profile)
    log_progress("Precompute stage 0: built structured JD understanding", quiet)
    log_progress("Precompute pass 1: building JD-term document statistics", quiet)
    candidate_count, avg_doc_length, doc_freq = document_stats(
        candidates_path,
        weights,
        progress_every=progress_every,
        quiet=quiet,
    )

    rows = []
    max_bm25 = 0.0
    started_at = time.perf_counter()
    log_progress("Precompute pass 2: scoring semantic and structured features", quiet)
    for seen, candidate in enumerate(iter_candidates(candidates_path), start=1):
        counts = Counter(tokenize(candidate_text(candidate)))
        doc_length = sum(counts.values())
        semantic_raw = bm25_score(
            counts,
            doc_length,
            candidate_count,
            avg_doc_length,
            doc_freq,
            weights,
        )
        base_score, components = score_candidate(candidate, jd_profile=jd_profile)
        max_bm25 = max(max_bm25, semantic_raw)
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "base_score": base_score,
                "semantic_raw": semantic_raw,
                "components": components,
            }
        )

        if progress_every and seen % progress_every == 0:
            elapsed = max(time.perf_counter() - started_at, 0.001)
            log_progress(
                (
                    f"Precompute pass 2: {seen:,} candidates "
                    f"({seen / elapsed:,.0f}/sec)"
                ),
                quiet,
            )

    raw_scores = sorted(row["semantic_raw"] for row in rows)
    scale_index = int(0.98 * (len(raw_scores) - 1)) if raw_scores else 0
    semantic_scale = max(raw_scores[scale_index] if raw_scores else max_bm25, 1.0)
    for row in rows:
        row["semantic_score"] = clamp(row["semantic_raw"] / semantic_scale)
        row["features"] = feature_vector(row)
        row["coverage_score"] = fixed_coverage_score(row["features"])
        row["hybrid_score"] = clamp(
            0.52 * row["semantic_score"]
            + 0.33 * row["coverage_score"]
            + 0.15 * row["base_score"]
        )

    ranked = sorted(rows, key=lambda row: (-row["hybrid_score"], row["candidate_id"]))
    artifact_rows = ranked[:artifact_limit] if artifact_limit else ranked
    candidates = {
        row["candidate_id"]: {
            "semantic_score": round(row["semantic_score"], 6),
            "coverage_score": round(row["coverage_score"], 6),
            "hybrid_score": round(row["hybrid_score"], 6),
            "precompute_rank": rank,
        }
        for rank, row in enumerate(artifact_rows, start=1)
    }
    artifact = {
        "metadata": {
            "version": 2,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_candidates": str(candidates_path),
            "candidate_count": candidate_count,
            "artifact_candidate_count": len(candidates),
            "avg_doc_length": round(avg_doc_length, 3),
            "semantic_scale": round(semantic_scale, 6),
            "artifact_limit": artifact_limit,
            "method": "BM25-style semantic retrieval + fixed JD coverage scoring",
            "jd_understanding": {
                "role": jd_profile["role"],
                "source": jd_profile.get("source", "default"),
                "core_mandate": jd_profile["core_mandate"],
                "ideal_profile": json_safe(jd_profile["ideal_profile"]),
                "query_term_count": len(jd_retrieval_terms(jd_profile)),
                "query_token_count": len(weights),
            },
            "coverage_weights": {
                name: round(value, 6)
                for name, value in normalized_weights(FIXED_COVERAGE_WEIGHTS).items()
            },
        },
        "candidates": candidates,
    }
    write_precomputed_signals(artifact, output_path)
    log_progress(
        f"Wrote {len(candidates):,} precomputed rank signals to {output_path}",
        quiet,
    )
    return artifact
