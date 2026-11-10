"""Validated, atomic JSON persistence for course scores and personal bests."""

import json
import os
import re
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any

import config

_SCHEMA_VERSION = 1
_MAX_RUNS_PER_COURSE = 100


class ScoreStorageError(OSError):
    """Report a score-file read, validation, or write failure to the UI."""


def load_scores(path: Path | None = None) -> dict[str, Any]:
    """Load score records, returning a fresh valid store when no file exists."""
    path = config.SCORES_FILE if path is None else path
    try:
        with path.open("r", encoding="utf-8") as score_file:
            data = json.load(score_file)
    except FileNotFoundError:
        return _empty_store()
    except (json.JSONDecodeError, OSError) as error:
        raise ScoreStorageError(f"Could not read score data at {path}: {error}") from error
    if not _is_valid_store(data):
        raise ScoreStorageError(f"Score data at {path} has an unsupported structure.")
    return data


def unlocked_levels(domain: str, path: Path | None = None) -> frozenset[str]:
    """Return sequentially unlocked difficulty levels for one learning domain."""
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("A learning domain is required to check level progress.")
    data = load_scores(path)
    course_key = _slug(domain)
    completed = {
        course["level"].casefold()
        for key, course in data["courses"].items()
        if key.startswith(f"{course_key}_")
        and any(run["completed"] for run in course["runs"])
    }
    unlocked = {"Beginner"}
    if "beginner" in completed:
        unlocked.add("Intermediate")
    if "intermediate" in completed:
        unlocked.add("Advanced")
    return frozenset(unlocked)


def record_result(
    domain: str,
    level: str,
    score: int,
    accuracy: float,
    elapsed_seconds: float,
    completed: bool,
    path: Path | None = None,
) -> dict[str, Any]:
    """Append one run and update the best time for its course if completed."""
    if (
        not isinstance(domain, str)
        or not isinstance(level, str)
        or not domain.strip()
        or not level.strip()
    ):
        raise ValueError("A domain and level are required to record a result.")
    if (
        not isinstance(score, int)
        or isinstance(score, bool)
        or score < 0
        or not isinstance(accuracy, (int, float))
        or isinstance(accuracy, bool)
        or not isfinite(accuracy)
        or not 0.0 <= accuracy <= 100.0
        or not isinstance(elapsed_seconds, (int, float))
        or isinstance(elapsed_seconds, bool)
        or not isfinite(elapsed_seconds)
        or elapsed_seconds < 0
        or not isinstance(completed, bool)
    ):
        raise ValueError("Score, accuracy, and elapsed time are outside valid ranges.")

    path = config.SCORES_FILE if path is None else path
    data = load_scores(path)
    course_key = f"{_slug(domain)}_{_slug(level)}"
    course = data["courses"].setdefault(
        course_key,
        {
            "domain": domain,
            "level": level,
            "best_time_seconds": None,
            "best_score": 0,
            "runs": [],
        },
    )
    run = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "accuracy": round(accuracy, 2),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "completed": completed,
    }
    course["runs"].append(run)
    course["runs"] = course["runs"][-_MAX_RUNS_PER_COURSE:]
    course["best_score"] = max(course["best_score"], score)

    is_best_time = False
    if completed and (
        course["best_time_seconds"] is None
        or elapsed_seconds < course["best_time_seconds"]
    ):
        course["best_time_seconds"] = round(elapsed_seconds, 2)
        is_best_time = True

    _write_store(path, data)
    return {
        "course": course,
        "run": run,
        "is_best_time": is_best_time,
    }


def _empty_store() -> dict[str, Any]:
    """Create the versioned top-level score structure."""
    return {"version": _SCHEMA_VERSION, "courses": {}}


def _is_valid_store(data: Any) -> bool:
    """Check that the parsed JSON has this application's versioned shape."""
    if not isinstance(data, dict):
        return False
    if data.get("version") != _SCHEMA_VERSION or not isinstance(data.get("courses"), dict):
        return False
    for course in data["courses"].values():
        if (
            not isinstance(course, dict)
            or not isinstance(course.get("domain"), str)
            or not isinstance(course.get("level"), str)
            or not isinstance(course.get("best_score"), int)
            or isinstance(course.get("best_score"), bool)
            or course["best_score"] < 0
            or not isinstance(course.get("runs"), list)
            or (
                course.get("best_time_seconds") is not None
                and (
                    not isinstance(course.get("best_time_seconds"), (int, float))
                    or isinstance(course.get("best_time_seconds"), bool)
                    or not isfinite(course["best_time_seconds"])
                    or course["best_time_seconds"] < 0
                )
            )
            or not all(_is_valid_run(run) for run in course.get("runs", []))
        ):
            return False
    return True


def _is_valid_run(run: Any) -> bool:
    """Validate the required fields in one persisted result entry."""
    return (
        isinstance(run, dict)
        and isinstance(run.get("recorded_at"), str)
        and isinstance(run.get("score"), int)
        and not isinstance(run.get("score"), bool)
        and run["score"] >= 0
        and isinstance(run.get("accuracy"), (int, float))
        and not isinstance(run.get("accuracy"), bool)
        and isfinite(run["accuracy"])
        and 0 <= run["accuracy"] <= 100
        and isinstance(run.get("elapsed_seconds"), (int, float))
        and not isinstance(run.get("elapsed_seconds"), bool)
        and isfinite(run["elapsed_seconds"])
        and run["elapsed_seconds"] >= 0
        and isinstance(run.get("completed"), bool)
    )


def _write_store(path: Path, data: dict[str, Any]) -> None:
    """Write JSON to a sibling temporary file and atomically replace the store."""
    temporary_path = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8") as score_file:
            json.dump(data, score_file, indent=2, ensure_ascii=False)
            score_file.write("\n")
            score_file.flush()
            os.fsync(score_file.fileno())
        temporary_path.replace(path)
    except OSError as error:
        raise ScoreStorageError(f"Could not save score data at {path}: {error}") from error


def _slug(value: str) -> str:
    """Create a stable lowercase key from a course label."""
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
