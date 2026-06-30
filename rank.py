#!/usr/bin/env python3
import argparse
from pathlib import Path

from utils.ranking.config import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PRECOMPUTE_PATH,
    DEFAULT_PROGRESS_EVERY,
    TOP_N,
)
from utils.ranking.io import (
    log_progress,
    resolve_candidate_path,
    write_diagnostics,
    write_submission,
)
from utils.ranking.ranker import rank_candidates


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rank candidates for the Redrob Senior AI Engineer JD."
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
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output submission CSV path. Defaults to {DEFAULT_OUTPUT_PATH}.",
    )
    parser.add_argument(
        "--diagnostics-out",
        help="Optional CSV path for score component diagnostics.",
    )
    parser.add_argument(
        "--precompute-artifact",
        help=(
            "Optional offline semantic/coverage signal artifact. If omitted, "
            f"{DEFAULT_PRECOMPUTE_PATH} is used when present."
        ),
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
    parser.add_argument("--top-n", type=int, default=TOP_N, help="Number of rows to emit.")
    return parser.parse_args()


def main():
    args = parse_args()
    candidates_path = resolve_candidate_path(args.candidates)
    precompute_artifact = args.precompute_artifact
    if precompute_artifact is None and Path(DEFAULT_PRECOMPUTE_PATH).exists():
        precompute_artifact = DEFAULT_PRECOMPUTE_PATH

    rows = rank_candidates(
        candidates_path,
        top_n=args.top_n,
        progress_every=args.progress_every,
        quiet=args.quiet,
        precompute_artifact=precompute_artifact,
    )
    write_submission(rows, args.out)
    if args.diagnostics_out:
        write_diagnostics(rows, args.diagnostics_out)

    log_progress(f"Wrote submission to {args.out}", args.quiet)
    if args.diagnostics_out:
        log_progress(f"Wrote diagnostics to {args.diagnostics_out}", args.quiet)


if __name__ == "__main__":
    main()
