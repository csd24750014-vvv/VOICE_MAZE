"""Load and validate the shared JSON format for all course learning content."""

import json
import re
from typing import Any, cast

import config


class ContentLoadError(ValueError):
    """Explain why a selected domain and difficulty cannot be loaded."""


def course_filename(domain: str, level: str) -> str:
    """Return the stable JSON filename for one selected course."""
    return f"{_slug(domain)}_{_slug(level)}.json"


def load_course(domain: str, level: str) -> list[dict[str, Any]]:
    """Load five validated topics and their three multiple-choice questions."""
    filename = course_filename(domain, level)
    content_path = config.PROJECT_ROOT / "content" / filename
    try:
        with content_path.open("r", encoding="utf-8") as content_file:
            data = json.load(content_file)
    except FileNotFoundError as error:
        raise ContentLoadError(f"Missing course file: content/{filename}.") from error
    except (json.JSONDecodeError, OSError) as error:
        raise ContentLoadError(f"Could not read content/{filename}: {error}.") from error

    if not isinstance(data, dict) or not isinstance(data.get("topics"), list):
        raise ContentLoadError(f"Course file content/{filename} must contain a topics list.")
    topics = data["topics"]
    if len(topics) != 5:
        raise ContentLoadError(f"Course file content/{filename} must contain exactly five topics.")
    for topic_index, topic in enumerate(topics, start=1):
        _validate_topic(topic, filename, topic_index)
    return topics


def normalize_answer(value: str) -> str:
    """Normalize answer text for punctuation-insensitive option matching."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def question_options(question: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return exactly four display strings from list- or letter-keyed JSON."""
    raw_options = question.get("options")
    if isinstance(raw_options, dict):
        options = tuple(raw_options.get(letter, "") for letter in "ABCD")
    elif isinstance(raw_options, list):
        options = tuple(raw_options)
    else:
        options = ()
    if len(options) != 4 or not all(isinstance(option, str) and option.strip() for option in options):
        raise ContentLoadError("A question must have four non-empty text options.")
    return cast(
        tuple[str, str, str, str],
        tuple(option.strip() for option in options),
    )


def correct_option_index(question: dict[str, Any]) -> int:
    """Resolve a correct answer expressed as A–D or as the full answer text."""
    answer = question.get("correct_answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ContentLoadError("A question must include its correct_answer text or letter.")
    normalized = normalize_answer(answer)
    if normalized in {"a", "b", "c", "d"}:
        return ord(normalized) - ord("a")
    options = question_options(question)
    normalized_options = [normalize_answer(option) for option in options]
    if normalized not in normalized_options:
        raise ContentLoadError("A question's correct_answer must match one of its options.")
    return normalized_options.index(normalized)


def _validate_topic(topic: Any, filename: str, topic_index: int) -> None:
    """Reject malformed notes and quiz entries before they reach a scene."""
    prefix = f"Topic {topic_index} in content/{filename}"
    if (
        not isinstance(topic, dict)
        or not isinstance(topic.get("title"), str)
        or not topic["title"].strip()
        or not isinstance(topic.get("notes"), list)
        or not 4 <= len(topic["notes"]) <= 6
        or not all(isinstance(note, str) and note.strip() for note in topic["notes"])
        or not isinstance(topic.get("example"), str)
        or not topic["example"].strip()
        or not isinstance(topic.get("example_output"), str)
        or not topic["example_output"].strip()
    ):
        raise ContentLoadError(
            f"{prefix} needs a title, 4–6 notes, an example, and its expected output."
        )

    questions = topic.get("mcqs")
    if not isinstance(questions, list) or len(questions) != 3:
        raise ContentLoadError(f"{prefix} must contain exactly three MCQs.")
    for question_index, question in enumerate(questions, start=1):
        if (
            not isinstance(question, dict)
            or not isinstance(question.get("question"), str)
            or not question["question"].strip()
            or not isinstance(question.get("explanation"), str)
            or not question["explanation"].strip()
        ):
            raise ContentLoadError(
                f"{prefix}, question {question_index} needs a question and explanation."
            )
        try:
            question_options(question)
            correct_option_index(question)
        except ContentLoadError as error:
            raise ContentLoadError(
                f"{prefix}, question {question_index}: {error}"
            ) from error


def _slug(value: str) -> str:
    """Convert a course label into the stable lowercase filename form."""
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
