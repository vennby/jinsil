import heapq
import time

from .config import DEFAULT_PROGRESS_EVERY, HEAP_SIZE, TOP_N
from .io import iter_candidates, log_progress
from .reasoning import make_reasoning
from .scoring import score_candidate


def rank_candidates(
    candidates_path,
    top_n=TOP_N,
    heap_size=HEAP_SIZE,
    progress_every=DEFAULT_PROGRESS_EVERY,
    quiet=False,
):
    heap = []
    started_at = time.perf_counter()
    seen = 0

    log_progress(f"Starting ranking from {candidates_path}", quiet)
    for candidate in iter_candidates(candidates_path):
        seen += 1
        score, components = score_candidate(candidate)
        candidate_id = candidate["candidate_id"]
        entry = (score, candidate_id, candidate, components)

        if len(heap) < heap_size:
            heapq.heappush(heap, entry)
        elif entry > heap[0]:
            heapq.heapreplace(heap, entry)

        if progress_every and seen % progress_every == 0:
            elapsed = max(time.perf_counter() - started_at, 0.001)
            rate = seen / elapsed
            threshold = heap[0][0] if heap else 0.0
            log_progress(
                (
                    f"Processed {seen:,} candidates "
                    f"({rate:,.0f}/sec); heap={len(heap):,}; "
                    f"current top-{min(heap_size, seen)} cutoff={threshold:.4f}"
                ),
                quiet,
            )

    ranked = sorted(heap, key=lambda row: (-row[0], row[1]))[:top_n]
    elapsed = max(time.perf_counter() - started_at, 0.001)
    log_progress(
        (
            f"Finished scoring {seen:,} candidates in {elapsed:.1f}s "
            f"({seen / elapsed:,.0f}/sec). Writing top {len(ranked)}."
        ),
        quiet,
    )

    rows = []
    for rank, (score, _candidate_id, candidate, components) in enumerate(ranked, start=1):
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "rank": rank,
                "score": f"{score:.6f}",
                "reasoning": make_reasoning(candidate, components),
                "_components": components,
            }
        )
    return rows
