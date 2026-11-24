from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

from .prefrontal_cortex import PrefrontalCognitiveController


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    case_id: str
    goal: str
    candidates: tuple[Mapping[str, Any], ...]
    relevant_ids: frozenset[str]
    expected_source_refs: Mapping[str, str]


def load_cases(dataset_path: Path) -> list[RetrievalEvaluationCase]:
    """Load a versioned, synthetic retrieval benchmark from JSON."""
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    raw_cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("The retrieval benchmark must contain a non-empty cases list.")

    cases: list[RetrievalEvaluationCase] = []
    seen_case_ids: set[str] = set()
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError("Each retrieval benchmark case must be an object.")

        case_id = str(raw.get("case_id", "")).strip()
        goal = str(raw.get("goal", "")).strip()
        candidates = raw.get("candidates")
        relevant_ids = raw.get("relevant_ids", [])
        source_refs = raw.get("expected_source_refs", {})

        if not case_id or not goal:
            raise ValueError("Every retrieval benchmark case needs a case_id and goal.")
        if case_id in seen_case_ids:
            raise ValueError(f"Duplicate retrieval benchmark case_id: {case_id}")
        if not isinstance(candidates, list) or not isinstance(relevant_ids, list):
            raise ValueError(
                f"Case {case_id} must provide candidates and relevant_ids lists."
            )
        if not isinstance(source_refs, dict):
            raise ValueError(f"Case {case_id} expected_source_refs must be an object.")

        candidate_ids = [
            str(item.get("id", ""))
            for item in candidates
            if isinstance(item, dict)
        ]
        if len(candidate_ids) != len(candidates) or any(
            not item_id for item_id in candidate_ids
        ):
            raise ValueError(f"Every candidate in case {case_id} needs a non-empty id.")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"Case {case_id} contains duplicate candidate ids.")

        seen_case_ids.add(case_id)
        cases.append(
            RetrievalEvaluationCase(
                case_id=case_id,
                goal=goal,
                candidates=tuple(candidates),
                relevant_ids=frozenset(str(item_id) for item_id in relevant_ids),
                expected_source_refs={
                    str(item_id): str(source_ref)
                    for item_id, source_ref in source_refs.items()
                },
            )
        )
    return cases


def _dcg(relevance: Sequence[int]) -> float:
    return sum(
        value / math.log2(index + 2)
        for index, value in enumerate(relevance)
    )


def _mean(values: Sequence[float]) -> float:
    return round(fmean(values), 4) if values else 0.0


def evaluate_case(
    case: RetrievalEvaluationCase,
    *,
    controller: PrefrontalCognitiveController | None = None,
    k: int = 3,
) -> dict[str, Any]:
    """Evaluate the deterministic attention/ranking stage for one case.

    Precision uses the conventional fixed-k denominator. Recall is measured
    against all labelled relevant IDs, including any absent from the candidate
    pool, so upstream candidate-generation misses remain visible.
    """
    if k < 1:
        raise ValueError("k must be at least 1.")

    ranker = controller or PrefrontalCognitiveController()
    selected = ranker.select_relevant(case.goal, case.candidates, limit=k)
    ranked_ids = [str(item.get("id", "")) for item in selected]
    if any(not item_id for item_id in ranked_ids):
        raise ValueError(f"Case {case.case_id} selected a candidate without an id.")

    hits = [item_id for item_id in ranked_ids if item_id in case.relevant_ids]
    precision = len(hits) / k
    recall = len(set(hits)) / len(case.relevant_ids) if case.relevant_ids else None

    first_relevant_rank = next(
        (index for index, item_id in enumerate(ranked_ids, start=1)
         if item_id in case.relevant_ids),
        None,
    )
    reciprocal_rank = 1.0 / first_relevant_rank if first_relevant_rank else 0.0

    ranked_relevance = [
        1 if item_id in case.relevant_ids else 0 for item_id in ranked_ids
    ]
    ideal_relevance = [1] * min(k, len(case.relevant_ids))
    ideal_dcg = _dcg(ideal_relevance)
    ndcg = _dcg(ranked_relevance) / ideal_dcg if ideal_dcg else None

    selected_by_id = {str(item.get("id")): item for item in selected}
    source_checks = [
        (item_id, selected_by_id[item_id].get("source_ref"))
        for item_id in ranked_ids
        if item_id in case.expected_source_refs
    ]
    source_fidelity = (
        sum(
            source_ref == case.expected_source_refs[item_id]
            for item_id, source_ref in source_checks
        ) / len(source_checks)
        if source_checks else None
    )

    abstention_correct = (
        not ranked_ids if not case.relevant_ids else None
    )
    return {
        "case_id": case.case_id,
        "goal": case.goal,
        "retrieved_ids": ranked_ids,
        "relevant_ids": sorted(case.relevant_ids),
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4) if recall is not None else None,
        "reciprocal_rank": round(reciprocal_rank, 4),
        "ndcg_at_k": round(ndcg, 4) if ndcg is not None else None,
        "source_reference_fidelity": (
            round(source_fidelity, 4)
            if source_fidelity is not None
            else None
        ),
        "abstention_correct": abstention_correct,
    }


def evaluate_dataset(
    cases: Sequence[RetrievalEvaluationCase],
    *,
    k: int = 3,
) -> dict[str, Any]:
    """Return macro-averaged ranking metrics plus a separate abstention score."""
    if not cases:
        raise ValueError("At least one retrieval benchmark case is required.")
    if k < 1:
        raise ValueError("k must be at least 1.")

    reports = [evaluate_case(case, k=k) for case in cases]
    evidence_reports = [report for report in reports if report["relevant_ids"]]
    no_evidence_reports = [
        report for report in reports if not report["relevant_ids"]
    ]
    source_scores = [
        report["source_reference_fidelity"]
        for report in evidence_reports
        if report["source_reference_fidelity"] is not None
    ]
    correct_abstentions = sum(
        report["abstention_correct"] is True for report in no_evidence_reports
    )

    summary = {
        "cases": len(reports),
        "evidence_cases": len(evidence_reports),
        "no_evidence_cases": len(no_evidence_reports),
        "k": k,
        "precision_at_k": _mean(
            [report["precision_at_k"] for report in evidence_reports]
        ),
        "recall_at_k": _mean([
            report["recall_at_k"] for report in evidence_reports
            if report["recall_at_k"] is not None
        ]),
        "mrr": _mean([report["reciprocal_rank"] for report in evidence_reports]),
        "ndcg_at_k": _mean([
            report["ndcg_at_k"] for report in evidence_reports
            if report["ndcg_at_k"] is not None
        ]),
        "source_reference_fidelity": _mean(source_scores),
        "abstention_accuracy": (
            round(correct_abstentions / len(no_evidence_reports), 4)
            if no_evidence_reports else None
        ),
    }
    return {
        "evaluation_scope": (
            "Deterministic post-retrieval attention/ranking only. "
            "Candidate generation, LLM answer correctness, biological equivalence, "
            "and real-user privacy properties are not measured by this benchmark."
        ),
        "summary": summary,
        "case_results": reports,
    }


def main(argv: Sequence[str] | None = None) -> int:
    backend_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(
        description="Run Cerepath's deterministic cognitive retrieval benchmark."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=backend_root / "evals" / "cognitive_retrieval_v1.json",
        help="Path to a versioned retrieval benchmark JSON file.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of ranked results to evaluate.",
    )
    args = parser.parse_args(argv)

    result = evaluate_dataset(load_cases(args.dataset), k=args.k)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
