from typing import List

import pytest

from .framework import (
    EvalCase,
    EvalHooks,
    EvalResultWithSummary,
    Evaluator,
    run_evaluator,
)
from .score import Score, Scorer


@pytest.mark.asyncio
async def test_run_evaluator_basic():
    """Test that run_evaluator correctly processes a simple evaluation."""
    # Define test data
    data = [
        EvalCase(input=1, expected=2),
        EvalCase(input=2, expected=4),
        EvalCase(input=3, expected=6),
    ]

    # Define a simple task function
    def multiply_by_two(input_value):
        return input_value * 2

    # Define a simple scoring function
    def exact_match(input_value, output, expected):
        return 1.0 if output == expected else 0.0

    # Create evaluator
    evaluator = Evaluator(
        project_name="test-project",
        eval_name="test-evaluator",
        data=data,
        task=multiply_by_two,
        scores=[exact_match],
        experiment_name=None,
        metadata=None,
    )

    # Run evaluator
    result = await run_evaluator(experiment=None, evaluator=evaluator, position=None, filters=[])

    # Verify results
    assert isinstance(result, EvalResultWithSummary)
    assert len(result.results) == 3

    # Check individual results
    for i, eval_result in enumerate(result.results):
        input_value = i + 1
        expected_value = input_value * 2

        assert eval_result.input == input_value
        assert eval_result.expected == expected_value
        assert eval_result.output == expected_value
        assert eval_result.scores.get("exact_match") == 1.0
        assert eval_result.error is None

    # Verify summary
    assert result.summary.project_name == "test-project"
    assert "exact_match" in result.summary.scores
    assert result.summary.scores["exact_match"].score == 1.0


@pytest.mark.asyncio
async def test_run_evaluator_with_many_scorers():
    # This test validates that we can process scores from any sources. It is nox's job
    # to ensure this test runs with and without autoevals and braintrust_core installed.
    try:
        from braintrust_core.score import Score as BraintrustCoreScore
    except ImportError:
        from .score import Score as BraintrustCoreScore

    # Define test data
    data = [
        EvalCase(input="abc", expected="abc"),
        EvalCase(input="def", expected="def"),
    ]

    def simple_task(input_value):
        return input_value

    def dict_scorer(input_value, output, expected):
        return {"name": "dict_scorer", "score": 1.0}

    def core_scorer(input_value, output, expected):
        return BraintrustCoreScore(name="core_scorer", score=1.0)

    def scorer(input_value, output, expected):
        return Score(name="scorer", score=1.0)

    class CustomScorer(Scorer):
        def _run_eval_sync(self, *args, **kwargs):
            return Score(name="custom_scorer", score=1.0)

    class CustomScorerAsync(Scorer):
        async def eval_async(self, *args, **kwargs):
            return Score(name="custom_async_scorer", score=1.0)

        def _run_eval_sync(self, *args, **kwargs):
            return Score(name="custom_async_scorer", score=1.0)

    scorers = [
        dict_scorer,
        core_scorer,
        scorer,
        CustomScorer(),
        CustomScorerAsync(),
    ]
    scorer_names = [
        "core_scorer",
        "scorer",
        "dict_scorer",
        "custom_scorer",
        "custom_async_scorer",
    ]

    # if autoevals is installed, use it. This verifies our scoring duck typing works
    try:
        from autoevals import Levenshtein

        scorers.append(Levenshtein())
        scorer_names.append("Levenshtein")
        scorers.append(Levenshtein)
        scorer_names.append("Levenshtein")
    except ImportError:
        pass

    # Create evaluator with all scorers
    evaluator = Evaluator(
        project_name="test-project",
        eval_name="test-multiple-score-classes",
        data=data,
        task=simple_task,
        scores=scorers,
        experiment_name=None,
        metadata=None,
    )

    # Run evaluator
    result = await run_evaluator(None, evaluator, None, [])

    assert isinstance(result, EvalResultWithSummary)
    assert len(result.results) == 2

    # All scorers should produce the same scores
    for eval_result in result.results:
        for scorer_name in scorer_names:
            print(eval_result.scores)
            assert scorer_name in eval_result.scores
            assert eval_result.scores[scorer_name] == 1.0

    assert result.summary.project_name == "test-project"
    for scorer_name in scorer_names:
        assert scorer_name in result.summary.scores
        assert result.summary.scores[scorer_name].score == 1.0


@pytest.mark.asyncio
async def test_hooks_trial_index():
    """Test that trial_index is correctly passed to task via hooks."""
    trial_indices: List[int] = []

    # Task that captures trial indices
    def task_with_hooks(input_value: int, hooks: EvalHooks) -> int:
        trial_indices.append(hooks.trial_index)
        return input_value * 2

    # Create evaluator with trial_count > 1
    evaluator = Evaluator(
        project_name="test-project",
        eval_name="test-trial-index",
        data=[EvalCase(input=1, expected=2)],
        task=task_with_hooks,
        scores=[],  # No scoring needed for this test
        experiment_name=None,
        metadata=None,
        trial_count=3,  # Run 3 trials
    )

    # Run evaluator
    result = await run_evaluator(experiment=None, evaluator=evaluator, position=None, filters=[])

    # Verify we got 3 results (one for each trial)
    assert len(result.results) == 3

    # Verify trial indices were captured correctly
    assert len(trial_indices) == 3
    assert sorted(trial_indices) == [0, 1, 2]

    # Verify all results are correct
    for eval_result in result.results:
        assert eval_result.input == 1
        assert eval_result.expected == 2
        assert eval_result.output == 2  # 1 * 2
        assert eval_result.error is None


@pytest.mark.asyncio
async def test_hooks_trial_index_multiple_inputs():
    """Test trial_index with multiple inputs to ensure proper indexing."""
    trial_data: List[tuple] = []  # (input, trial_index)

    def task_with_hooks(input_value: int, hooks: EvalHooks) -> int:
        trial_data.append((input_value, hooks.trial_index))
        return input_value * 2

    # Create evaluator with multiple inputs and trials
    evaluator = Evaluator(
        project_name="test-project",
        eval_name="test-trial-index-multiple",
        data=[
            EvalCase(input=1, expected=2),
            EvalCase(input=2, expected=4),
        ],
        task=task_with_hooks,
        scores=[],
        experiment_name=None,
        metadata=None,
        trial_count=2,  # 2 trials per input
    )

    # Run evaluator
    result = await run_evaluator(experiment=None, evaluator=evaluator, position=None, filters=[])

    # Should have 4 results total (2 inputs × 2 trials)
    assert len(result.results) == 4
    assert len(trial_data) == 4

    # Group by input to verify trial indices
    input_1_trials = [trial_idx for inp, trial_idx in trial_data if inp == 1]
    input_2_trials = [trial_idx for inp, trial_idx in trial_data if inp == 2]

    # Each input should have been run with trial indices 0 and 1
    assert sorted(input_1_trials) == [0, 1]
    assert sorted(input_2_trials) == [0, 1]
