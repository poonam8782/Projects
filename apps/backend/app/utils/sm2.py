"""
SM-2 (SuperMemo 2) spaced repetition algorithm utilities.

This module implements the SM-2 algorithm originally described by Piotr Wozniak (1987)
for scheduling flashcard reviews to maximize long-term retention. It calculates updated
easiness factor (efactor), repetition count, next interval (in days), and next review
timestamp based on a user-provided quality rating for the latest review.

References:
- Wikipedia: https://en.wikipedia.org/wiki/SuperMemo#SM-2_algorithm
- Wozniak, P. A. (1987). Optimization of learning.

Algorithm overview:
- Quality ratings (0-5):
  0 = complete blackout
  1 = incorrect; correct answer seemed familiar
  2 = incorrect; correct answer seemed easy after seeing it
  3 = correct response, but difficult/slow
  4 = correct after some hesitation
  5 = perfect, immediate recall

- Passing grade: quality >= 3 increments repetitions and grows interval
- Failing grade: quality < 3 resets repetitions to 0 and interval to 1 day

Intervals:
- First successful review: 1 day
- Second successful review: 6 days
- Subsequent: previous_interval * efactor (rounded)

Notes:
- Efactor is clamped to a minimum of 1.3
- All timestamps use UTC to avoid DST issues
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Final

logger = logging.getLogger(__name__)


# SM-2 algorithm parameters/constants
MIN_EFACTOR: Final[float] = 1.3
DEFAULT_EFACTOR: Final[float] = 2.5
DEFAULT_REPETITIONS: Final[int] = 0
DEFAULT_INTERVAL: Final[int] = 1
MIN_QUALITY: Final[int] = 0
MAX_QUALITY: Final[int] = 5
PASSING_QUALITY: Final[int] = 3
# Maximum interval cap (in days) to avoid impractically distant reviews (~10 years)
MAX_INTERVAL_DAYS: Final[int] = 3650


@dataclass(frozen=True)
class SM2Result:
    """Result of SM-2 calculation containing updated scheduling parameters.

    Attributes:
        efactor: Updated easiness factor (>= 1.3)
        repetitions: Updated count of consecutive successful reviews
        interval: Next interval in days (>= 1)
        next_review: Timestamp for the next review (UTC)
    """

    efactor: float
    repetitions: int
    interval: int
    next_review: datetime


def calculate_sm2(
    quality: int,
    *,
    current_efactor: float = DEFAULT_EFACTOR,
    current_repetitions: int = DEFAULT_REPETITIONS,
    current_interval: int = DEFAULT_INTERVAL,
) -> SM2Result:
    """Calculate next review parameters using the SM-2 algorithm.

    Args:
        quality: Integer rating in [0, 5], where 0 = blackout and 5 = perfect recall.
        current_efactor: Current easiness factor (default 2.5 for new cards).
        current_repetitions: Current number of consecutive successful reviews (>= 0).
        current_interval: Current interval in days (>= 1).

    Returns:
        SM2Result: Updated efactor, repetitions, interval, and next_review (UTC).

    Raises:
        ValueError: If inputs are invalid (quality out of range, negative repetitions, etc.).

    Algorithm:
        Based on the SM-2 specification. If quality >= 3 (passing), increment repetitions and
        compute the next interval. If quality < 3 (failing), reset repetitions to 0 and interval
        to 1 day. Efactor is updated and clamped to a minimum of 1.3.
    """

    # Input validation
    if not isinstance(quality, int) or quality < MIN_QUALITY or quality > MAX_QUALITY:
        raise ValueError("Quality must be between 0 and 5 (inclusive)")
    # Clamp incoming efactor instead of rejecting persisted low values
    current_efactor = max(current_efactor, MIN_EFACTOR)
    if current_repetitions < 0:
        raise ValueError("Repetitions must be non-negative")
    if current_interval < 1:
        raise ValueError("Interval must be a positive integer (>= 1 day)")

    # Update efactor according to SM-2 formula
    # new_efactor = E' = E + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    q_delta = 5 - quality
    new_efactor = current_efactor + (0.1 - q_delta * (0.08 + q_delta * 0.02))
    if new_efactor < MIN_EFACTOR:
        new_efactor = MIN_EFACTOR

    # Determine new repetitions and interval
    if quality < PASSING_QUALITY:
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = current_repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            # Subsequent reviews multiply the previous interval by the (updated) efactor
            new_interval = round(current_interval * new_efactor)
        if new_interval < 1:
            new_interval = 1

    # Cap interval to MAX_INTERVAL_DAYS to prevent excessively long scheduling
    if new_interval > MAX_INTERVAL_DAYS:
        new_interval = MAX_INTERVAL_DAYS

    now = datetime.now(timezone.utc)
    next_review = now + timedelta(days=new_interval)

    logger.debug(
        "SM-2 calculation: quality=%s, efactor=%.4f->%.4f, reps=%s->%s, interval=%s->%s, next=%s",
        quality,
        current_efactor,
        new_efactor,
        current_repetitions,
        new_repetitions,
        current_interval,
        new_interval,
        next_review.isoformat(),
    )

    return SM2Result(
        efactor=new_efactor,
        repetitions=new_repetitions,
        interval=new_interval,
        next_review=next_review,
    )


def get_due_flashcards_query(user_id: str, limit: int = 10) -> tuple[str, tuple]:
    """Generate a parameterized SQL query to fetch due flashcards for a user.

    Returns a tuple of (query, params) suitable for cursor.execute(query, params)
    to eliminate SQL injection risk.

    Args:
        user_id: The user's identifier.
        limit: Maximum number of rows to return.

    Returns:
        (query, params): SQL with %s placeholders and a params tuple.
    """
    if not user_id:
        raise ValueError("user_id must be a non-empty string")
    if limit <= 0:
        raise ValueError("limit must be a positive integer")
    query = (
        "SELECT * FROM flashcards WHERE user_id = %s AND next_review <= now() "
        "ORDER BY next_review ASC LIMIT %s"
    )
    params = (user_id, limit)
    return query, params


def format_interval_description(interval: int) -> str:
    """Convert an interval in days to a human-readable description.

    Examples:
        1 -> "1 day"
        6 -> "6 days"
        14 -> "2 weeks"
        30 -> "1 month"
        365 -> "1 year"

    Args:
        interval: Interval in days (>= 1)

    Returns:
        Human-readable description for UI display.
    """
    if interval <= 0:
        raise ValueError("interval must be >= 1")

    if interval == 1:
        return "1 day"
    if interval < 7:
        return f"{interval} days"
    if interval < 30:
        weeks = round(interval / 7)
        return f"{weeks} week" + ("s" if weeks != 1 else "")
    if interval < 365:
        months = round(interval / 30)
        return f"{months} month" + ("s" if months != 1 else "")
    years = round(interval / 365)
    return f"{years} year" + ("s" if years != 1 else "")


__all__ = [
    "MIN_EFACTOR",
    "DEFAULT_EFACTOR",
    "DEFAULT_REPETITIONS",
    "DEFAULT_INTERVAL",
    "MIN_QUALITY",
    "MAX_QUALITY",
    "PASSING_QUALITY",
    "MAX_INTERVAL_DAYS",
    "SM2Result",
    "calculate_sm2",
    "get_due_flashcards_query",
    "format_interval_description",
]
