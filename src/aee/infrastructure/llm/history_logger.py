"""LLM history logging utility."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def save_history(lm: Any, output_path: Path) -> int:
    """Save LLM history to JSON file.

    Args:
        lm: LLM instance with .history attribute
        output_path: Path to output file

    Returns:
        Number of entries saved
    """
    if not hasattr(lm, "history") or not lm.history:
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(lm.history, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(lm.history)} LLM calls to {output_path}")
    return len(lm.history)


def save_optimization_history(
    student_lm: Any,
    teacher_lm: Optional[Any],
    output_dir: Path,
    timestamp: Optional[str] = None,
) -> Dict[str, int]:
    """Save student and teacher LLM histories.

    Args:
        student_lm: Student LLM instance
        teacher_lm: Teacher LLM instance (optional)
        output_dir: Directory for output files
        timestamp: Optional timestamp string (default: current time)

    Returns:
        Dict with counts: {"student": N, "teacher": M}
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    counts: Dict[str, int] = {}

    student_count = save_history(
        student_lm,
        output_dir / f"student_lm_{timestamp}.json"
    )
    counts["student"] = student_count

    if teacher_lm is not None:
        teacher_count = save_history(
            teacher_lm,
            output_dir / f"teacher_lm_{timestamp}.json"
        )
        counts["teacher"] = teacher_count

    return counts
