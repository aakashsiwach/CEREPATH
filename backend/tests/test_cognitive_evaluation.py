from dataclasses import replace
from pathlib import Path

import pytest

from app.intelligence.cognitive.evaluation import (
    evaluate_case,
    evaluate_dataset,
    load_cases,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATASET = BACKEND_ROOT / "evals" / "cognitive_retrieval_v1.json"


def test_benchmark_dataset_has_relevant_and_abstention_cases():
    cases = load_cases(DATASET)
    assert len(cases) >= 6
    assert any(case.relevant_ids for case in cases)
    assert any(not case.relevant_ids for case in cases)


def test_evaluator_ranks_relevant_items_and_measures_source_fidelity():
    cases = load_cases(DATASET)
    case = next(
        case for case in cases
        if case.case_id == "semantic-java-collections"
    )

    result = evaluate_case(case, k=3)

    assert result["retrieved_ids"][:2] == [
        "java-collections-core",
        "java-collections-examples",
    ]
    assert result["precision_at_k"] == pytest.approx(2 / 3)
    assert result["recall_at_k"] == pytest.approx(1.0)
    assert result["reciprocal_rank"] == pytest.approx(1.0)
    assert result["ndcg_at_k"] == pytest.approx(1.0)
    assert result["source_reference_fidelity"] == pytest.approx(1.0)


def test_evaluator_abstains_when_no_local_evidence_exists():
    cases = load_cases(DATASET)
    case = next(
        case for case in cases
        if case.case_id == "no-local-evidence-abstention"
    )

    result = evaluate_case(case, k=3)

    assert result["retrieved_ids"] == []
    assert result["abstention_correct"] is True
    assert result["precision_at_k"] == 0.0
    assert result["recall_at_k"] is None


def test_dataset_summary_reports_macro_metrics_and_abstention():
    report = evaluate_dataset(load_cases(DATASET), k=3)

    assert report["summary"]["cases"] == 6
    assert report["summary"]["evidence_cases"] == 5
    assert report["summary"]["no_evidence_cases"] == 1
    assert report["summary"]["precision_at_k"] > 0.0
    assert report["summary"]["recall_at_k"] > 0.0
    assert report["summary"]["mrr"] > 0.0
    assert report["summary"]["ndcg_at_k"] > 0.0
    assert report["summary"]["source_reference_fidelity"] == pytest.approx(1.0)
    assert report["summary"]["abstention_accuracy"] == pytest.approx(1.0)


@pytest.mark.parametrize("k", [0, -1])
def test_evaluator_rejects_invalid_k(k):
    with pytest.raises(ValueError, match="k"):
        evaluate_dataset(load_cases(DATASET), k=k)


def test_evaluator_rejects_empty_dataset():
    with pytest.raises(ValueError, match="At least one"):
        evaluate_dataset([])


def test_load_cases_rejects_duplicate_case_ids(tmp_path):
    dataset = tmp_path / "duplicate.json"
    dataset.write_text(
        """
        {
          "cases": [
            {
              "case_id": "duplicate",
              "goal": "first",
              "candidates": [],
              "relevant_ids": []
            },
            {
              "case_id": "duplicate",
              "goal": "second",
              "candidates": [],
              "relevant_ids": []
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_cases(dataset)


def test_source_reference_fidelity_detects_a_wrong_source_reference():
    case = next(
        case for case in load_cases(DATASET)
        if case.case_id == "semantic-java-collections"
    )
    candidates = [dict(candidate) for candidate in case.candidates]
    candidates[0]["source_ref"] = "document:unrelated-source"

    report = evaluate_case(
        replace(case, candidates=tuple(candidates)),
        k=3,
    )

    assert report["source_reference_fidelity"] == pytest.approx(0.5)
