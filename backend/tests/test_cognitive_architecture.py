from app.intelligence.cognitive import (
    BaddeleyWorkingMemory,
    DigitalMind,
    HippocampalIndexer,
    MetacognitiveMonitor,
    PrefrontalCognitiveController,
    RewardPredictionError,
)


def test_baddeley_working_memory_is_bounded_and_keeps_recent_context():
    memory = BaddeleyWorkingMemory(capacity_items=3, capacity_characters=20)
    result = memory.retain([
        {"role": "user", "content": "old content"},
        {"role": "assistant", "content": "middle"},
        {"role": "user", "content": "latest"},
        {"role": "assistant", "content": "newest"},
    ])
    assert len(result) <= 3
    assert result[-1]["content"] == "newest"
    assert sum(len(item["content"]) for item in result) <= 20


def test_hippocampal_indexer_deduplicates_normalized_lesson_content():
    indexer = HippocampalIndexer()
    first = indexer.encode(title="Java", content="Collections   Framework")
    second = indexer.encode(title="Java", content="Collections Framework")
    assert first.content_sha256 == second.content_sha256
    assert first.episode_type == "lesson"
    assert len(first.content_sha256) == 64


def test_prefrontal_controller_selects_relevant_knowledge_only():
    controller = PrefrontalCognitiveController()
    selected = controller.select_relevant(
        "Explain Java collections",
        [
            {"title": "Java collections", "content": "Lists and maps", "confidence": 0.8},
            {"title": "Cooking", "content": "Pasta recipe", "confidence": 1.0},
        ],
    )
    assert len(selected) == 1
    assert selected[0]["title"] == "Java collections"
    assert selected[0]["attention_score"] > 0


def test_metacognitive_monitor_reports_retrieval_not_truth():
    monitor = MetacognitiveMonitor()
    result = monitor.assess_retrieval([])
    assert result.evidence_state == "no_local_evidence"
    assert "No matching" in result.explanation

    result = monitor.assess_retrieval([{"attention_score": 0.8}])
    assert result.evidence_state == "strong_retrieval_match"
    assert result.best_attention_score == 0.8


def test_reward_prediction_error_is_observed_minus_expected():
    result = RewardPredictionError.calculate(0.5, 1.0)
    assert result.delta == 0.5


def test_reward_prediction_error_rejects_out_of_range_values():
    try:
        RewardPredictionError.calculate(1.2, 0.0)
    except ValueError as exc:
        assert "between 0 and 1" in str(exc)
    else:
        raise AssertionError("Out-of-range reward should fail")


def test_digital_mind_coordinates_working_memory_attention_and_monitoring():
    mind = DigitalMind()
    context = mind.process_turn(
        current_goal="Explain Java collections",
        conversation_history=[
            {"role": "user", "content": "What is Java?"},
            {"role": "assistant", "content": "A programming language."},
        ],
        semantic_candidates=[
            {
                "title": "Java collections",
                "content": "Lists, sets, maps and queues",
                "confidence": 0.9,
            }
        ],
    )
    assert len(context.working_memory) == 2
    assert len(context.recalled_knowledge) == 1
    assert context.retrieval_assessment.evidence_state == "partial_retrieval_match"
