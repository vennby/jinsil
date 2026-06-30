#!/usr/bin/env python3
import argparse

from utils.ranking.config import DEFAULT_PRECOMPUTE_PATH, DEFAULT_PROGRESS_EVERY
from utils.ranking.io import resolve_candidate_path
from utils.ranking.precompute import compute_precompute_artifact


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build offline semantic retrieval and fixed JD coverage signals."
    )
    parser.add_argument(
        "--candidates",
        help=(
            "Path to candidates JSONL/JSON/GZ. If omitted, the CLI tries "
            "candidates.jsonl.gz, candidates.jsonl, then candidates.json."
        ),
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_PRECOMPUTE_PATH,
        help=f"Output artifact path. Defaults to {DEFAULT_PRECOMPUTE_PATH}.",
    )
    parser.add_argument(
        "--artifact-limit",
        type=int,
        default=15000,
        help="Number of top precomputed candidate signals to keep. Use 0 to keep all.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=DEFAULT_PROGRESS_EVERY,
        help=(
            "Print progress every N candidates. Use 0 to disable periodic updates. "
            f"Defaults to {DEFAULT_PROGRESS_EVERY}."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable progress logging.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    candidates_path = resolve_candidate_path(args.candidates)
    compute_precompute_artifact(
        candidates_path,
        output_path=args.out,
        artifact_limit=args.artifact_limit,
        progress_every=args.progress_every,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
