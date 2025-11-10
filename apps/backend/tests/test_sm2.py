"""Unit tests for the SM-2 spaced repetition algorithm utility (app.utils.sm2).

Tests cover:
- Basic functionality and return types
- Repetition and interval progression rules
- Efactor update formula and clamping
- Edge cases (boundary quality ratings, high repetitions)
- Error handling for invalid inputs
- Parametrized sequences and stability behaviors

Reference pattern: test_chunker.py for structure, fixtures, parametrization.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.utils.sm2 import (
    calculate_sm2,
    SM2Result,
    MIN_EFACTOR,
    DEFAULT_EFACTOR,
    PASSING_QUALITY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def new_card_params():
    """Return default parameters for a new flashcard (before first review)."""
    return {
        "quality": 4,
        "current_efactor": DEFAULT_EFACTOR,
        "current_repetitions": 0,
        "current_interval": 1,
    }


@pytest.fixture()
def established_card_params():
    """Return parameters for a card with several successful reviews."""
    return {
        "quality": 4,
        "current_efactor": 2.3,
        "current_repetitions": 5,
        "current_interval": 30,
    }


# ---------------------------------------------------------------------------
# Basic functionality tests
# ---------------------------------------------------------------------------


class TestCalculateSM2Basic:
    def test_calculate_sm2_returns_sm2result(self):
        result = calculate_sm2(quality=4)
        assert isinstance(result, SM2Result)
        assert isinstance(result.efactor, float)
        assert isinstance(result.repetitions, int)
        assert isinstance(result.interval, int)
        assert isinstance(result.next_review, datetime)

    def test_calculate_sm2_first_review_success(self):
        result = calculate_sm2(quality=4, current_repetitions=0, current_interval=1)
        assert result.repetitions == 1
        assert result.interval == 1
        delta = result.next_review - datetime.now(timezone.utc)
        assert 0.9 <= delta.total_seconds() / 86400 <= 1.1  # ~1 day tolerance

    def test_calculate_sm2_second_review_success(self):
        result = calculate_sm2(quality=4, current_repetitions=1, current_interval=1)
        assert result.repetitions == 2
        assert result.interval == 6
        delta = result.next_review - datetime.now(timezone.utc)
        assert 5.9 <= delta.total_seconds() / 86400 <= 6.1

    def test_calculate_sm2_subsequent_reviews(self):
        # Third successful review: interval = round(previous_interval * efactor)
        result = calculate_sm2(
            quality=4,
            current_efactor=2.5,
            current_repetitions=2,
            current_interval=6,
        )
        assert result.repetitions == 3
        assert result.interval == round(6 * result.efactor) or result.interval == round(6 * 2.5)
        assert result.interval >= 1

    def test_calculate_sm2_failed_review_resets(self):
        result = calculate_sm2(quality=2, current_repetitions=5, current_interval=30)
        assert result.repetitions == 0
        assert result.interval == 1
        delta_days = (result.next_review - datetime.now(timezone.utc)).total_seconds() / 86400
        assert 0.9 <= delta_days <= 1.1


# ---------------------------------------------------------------------------
# Efactor behavior tests
# ---------------------------------------------------------------------------


class TestCalculateSM2EFactor:
    def test_efactor_increases_with_high_quality(self):
        result = calculate_sm2(quality=5, current_efactor=2.5)
        assert result.efactor > 2.5

    def test_efactor_decreases_with_low_quality(self):
        result = calculate_sm2(quality=0, current_efactor=2.5)
        assert result.efactor < 2.5

    def test_efactor_clamped_to_minimum(self):
        # Repeated low quality should clamp at minimum
        ef = MIN_EFACTOR
        for _ in range(5):
            res = calculate_sm2(quality=0, current_efactor=ef)
            assert res.efactor >= MIN_EFACTOR
            ef = res.efactor

    def test_efactor_formula_correctness(self):
        # For quality=3, expected delta: 2.5 + (0.1 - 2 * (0.08 + 2 * 0.02)) = 2.36
        result = calculate_sm2(quality=3, current_efactor=2.5)
        assert result.efactor == pytest.approx(2.36, abs=0.02)


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestCalculateSM2EdgeCases:
    def test_quality_rating_boundary_values(self):
        # 0 (fail), 3 (pass), 5 (pass perfect)
        r0 = calculate_sm2(quality=0)
        assert r0.repetitions == 0 and r0.interval == 1
        r3 = calculate_sm2(quality=3)
        assert r3.repetitions == 1 and r3.interval == 1
        r5 = calculate_sm2(quality=5)
        assert r5.repetitions == 1 and r5.interval == 1

    def test_very_high_repetitions(self):
        result = calculate_sm2(
            quality=5,
            current_repetitions=100,
            current_interval=365,
            current_efactor=2.5,
        )
        assert result.repetitions == 101
        assert result.interval >= 365  # Should grow

    def test_next_review_timestamp_format(self):
        result = calculate_sm2(quality=4)
        assert isinstance(result.next_review, datetime)
        assert result.next_review.tzinfo is not None
        assert result.next_review > datetime.now(timezone.utc)

    def test_interval_never_zero(self):
        for q in range(0, 6):
            res = calculate_sm2(quality=q)
            assert res.interval >= 1


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestCalculateSM2ErrorHandling:
    def test_invalid_quality_too_low(self):
        with pytest.raises(ValueError) as exc:
            calculate_sm2(quality=-1)
        assert "Quality" in str(exc.value)

    def test_invalid_quality_too_high(self):
        with pytest.raises(ValueError) as exc:
            calculate_sm2(quality=6)
        assert "Quality" in str(exc.value)

    def test_invalid_efactor_too_low(self):
        # Efactor below minimum should be clamped, not raise
        result = calculate_sm2(quality=4, current_efactor=1.0)
        assert result.efactor >= MIN_EFACTOR

    def test_invalid_repetitions_negative(self):
        with pytest.raises(ValueError) as exc:
            calculate_sm2(quality=4, current_repetitions=-1)
        assert "Repetitions".lower() in str(exc.value).lower()

    def test_invalid_interval_zero(self):
        with pytest.raises(ValueError) as exc:
            calculate_sm2(quality=4, current_interval=0)
        assert "Interval".lower() in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Parametrized tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("quality", [0, 1, 2, 3, 4, 5])
def test_all_quality_ratings_parametrized(quality):
    result = calculate_sm2(quality=quality)
    if quality < PASSING_QUALITY:
        assert result.repetitions == 0
        assert result.interval == 1
    else:
        assert result.repetitions == 1
        assert result.interval == 1


def test_interval_progression_parametrized():
    # Simulate a sequence of successful reviews (quality=4)
    efactor = DEFAULT_EFACTOR
    repetitions = 0
    interval = 1
    intervals = []
    for _ in range(10):
        res = calculate_sm2(
            quality=4,
            current_efactor=efactor,
            current_repetitions=repetitions,
            current_interval=interval,
        )
        intervals.append(res.interval)
        efactor = res.efactor
        repetitions = res.repetitions
        interval = res.interval

    # Expect first two intervals fixed at 1 and 6, subsequent growth roughly exponential
    assert intervals[0] == 1
    assert intervals[1] == 6
    assert intervals[2] >= 6  # Should be >= previous interval
    assert all(i >= 1 for i in intervals)


def test_max_interval_cap():
    """Ensure extremely large intervals are capped at MAX_INTERVAL_DAYS."""
    from app.utils.sm2 import MAX_INTERVAL_DAYS

    # Simulate a very large previous interval and high efactor multiplication
    res = calculate_sm2(
        quality=5,
        current_efactor=2.5,
        current_repetitions=200,
        current_interval=MAX_INTERVAL_DAYS * 2,  # unrealistic large previous interval
    )
    assert res.interval == MAX_INTERVAL_DAYS


def test_failed_then_successful_reviews():
    # Sequence: success, success, fail, success, success
    res1 = calculate_sm2(quality=4)
    res2 = calculate_sm2(
        quality=4,
        current_efactor=res1.efactor,
        current_repetitions=res1.repetitions,
        current_interval=res1.interval,
    )
    res3 = calculate_sm2(
        quality=2,
        current_efactor=res2.efactor,
        current_repetitions=res2.repetitions,
        current_interval=res2.interval,
    )
    assert res3.repetitions == 0 and res3.interval == 1
    res4 = calculate_sm2(quality=4)
    assert res4.repetitions == 1 and res4.interval == 1
    res5 = calculate_sm2(
        quality=4,
        current_efactor=res4.efactor,
        current_repetitions=res4.repetitions,
        current_interval=res4.interval,
    )
    assert res5.repetitions == 2 and res5.interval == 6


def test_efactor_stability_with_quality_3():
    # Quality=3 should decrease efactor modestly but not below minimum unless very low
    ef = 2.5
    for _ in range(5):
        res = calculate_sm2(quality=3, current_efactor=ef)
        assert res.efactor >= MIN_EFACTOR
        ef = res.efactor
    # After several quality=3 reviews, efactor should have decreased but remain well above min
    assert ef < 2.5
    assert ef > MIN_EFACTOR


# ---------------------------------------------------------------------------
# Optional documentation-based test
# ---------------------------------------------------------------------------


def test_sm2_algorithm_documentation_example():
    """Test known example progression: 1 -> 6 -> ~interval*efactor growth."""
    # First review quality=4
    r1 = calculate_sm2(quality=4)
    assert r1.interval == 1
    # Second review
    r2 = calculate_sm2(
        quality=5,
        current_efactor=r1.efactor,
        current_repetitions=r1.repetitions,
        current_interval=r1.interval,
    )
    assert r2.interval == 6
    # Third review (quality=3) -> multiplication of previous interval by efactor
    r3 = calculate_sm2(
        quality=3,
        current_efactor=r2.efactor,
        current_repetitions=r2.repetitions,
        current_interval=r2.interval,
    )
    assert r3.interval >= 6  # Should be >= previous interval
