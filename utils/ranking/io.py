import csv
import gzip
import json
import sys
from pathlib import Path

from .config import DEFAULT_CANDIDATE_PATHS


def resolve_candidate_path(path=None):
    if path:
        return path

    for candidate_path in DEFAULT_CANDIDATE_PATHS:
        if Path(candidate_path).exists():
            return candidate_path

    searched = ", ".join(DEFAULT_CANDIDATE_PATHS)
    raise FileNotFoundError(
        f"No candidate file provided and none of these defaults exist: {searched}"
    )


def iter_candidates(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    mode = "rt" if path.suffix == ".gz" else "r"

    with opener(path, mode, encoding="utf-8") as file:
        first = file.read(1)
        file.seek(0)

        if first == "[":
            yield from json.load(file)
            return

        for line in file:
            line = line.strip()
            if line:
                yield json.loads(line)


def log_progress(message, quiet=False):
    if not quiet:
        print(message, file=sys.stderr, flush=True)


def load_precomputed_signals(path):
    if not path:
        return {}

    with open(path, "r", encoding="utf-8") as file:
        artifact = json.load(file)
    return artifact.get("candidates", {})


def write_precomputed_signals(artifact, output_path):
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(artifact, file, ensure_ascii=False, separators=(",", ":"))


def write_submission(rows, output_path):
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["candidate_id", "rank", "score", "reasoning"]
        )
        writer.writeheader()
        writer.writerows(
            {
                "candidate_id": row["candidate_id"],
                "rank": row["rank"],
                "score": row["score"],
                "reasoning": row["reasoning"],
            }
            for row in rows
        )


def write_diagnostics(rows, output_path):
    fieldnames = [
        "candidate_id",
        "rank",
        "score",
        "technical",
        "title",
        "career",
        "seniority",
        "product",
        "location",
        "engagement",
        "trust",
        "market",
        "penalty",
        "hireability_multiplier",
        "raw_score",
        "semantic_score",
        "coverage_score",
        "hybrid_score",
        "core_signal_count",
        "eval_signal_count",
        "evidence_depth",
        "hits",
        "penalty_reasons",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            components = row["_components"]
            writer.writerow(
                {
                    "candidate_id": row["candidate_id"],
                    "rank": row["rank"],
                    "score": row["score"],
                    "technical": f"{components['technical']:.4f}",
                    "title": f"{components['title']:.4f}",
                    "career": f"{components['career']:.4f}",
                    "seniority": f"{components['seniority']:.4f}",
                    "product": f"{components['product']:.4f}",
                    "location": f"{components['location']:.4f}",
                    "engagement": f"{components['engagement']:.4f}",
                    "trust": f"{components['trust']:.4f}",
                    "market": f"{components['market']:.4f}",
                    "penalty": f"{components['penalty']:.4f}",
                    "hireability_multiplier": f"{components['hireability_multiplier']:.4f}",
                    "raw_score": f"{components['raw_score']:.4f}",
                    "semantic_score": f"{components['semantic_score']:.4f}",
                    "coverage_score": f"{components['coverage_score']:.4f}",
                    "hybrid_score": f"{components['hybrid_score']:.4f}",
                    "core_signal_count": components["technical_details"]["core_signal_count"],
                    "eval_signal_count": components["technical_details"]["eval_signal_count"],
                    "evidence_depth": f"{components['evidence_depth']:.4f}",
                    "hits": "; ".join(components["hits"]),
                    "penalty_reasons": "; ".join(components["penalty_reasons"]),
                }
            )
