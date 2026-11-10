"""Normalize recognized phrases into predictable game actions."""

import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable, Optional

import config

_COMMANDS: dict[str, tuple[str, Optional[str]]] = {
    "start": ("start", None),
    "begin": ("start", None),
    "play": ("start", None),
    "how to play": ("how_to_play", None),
    "instructions": ("how_to_play", None),
    "help": ("how_to_play", None),
    "quit": ("quit", None),
    "exit": ("quit", None),
    "close game": ("quit", None),
    "next": ("next", None),
    "next page": ("next", None),
    "continue": ("next", None),
    "back": ("back", None),
    "previous": ("back", None),
    "previous page": ("back", None),
    "start maze": ("start_maze", None),
    "begin maze": ("start_maze", None),
    "go to maze": ("start_maze", None),
    "retry": ("retry", None),
    "try again": ("retry", None),
    "review again": ("retry", None),
    "play again": ("play_again", None),
    "replay": ("play_again", None),
    "main menu": ("main_menu", None),
    "return to menu": ("main_menu", None),
    "return to maze": ("return_to_maze", None),
    "view results": ("results", None),
    "up": ("move_up", None),
    "go up": ("move_up", None),
    "move up": ("move_up", None),
    "north": ("move_up", None),
    "down": ("move_down", None),
    "go down": ("move_down", None),
    "move down": ("move_down", None),
    "south": ("move_down", None),
    "left": ("move_left", None),
    "go left": ("move_left", None),
    "move left": ("move_left", None),
    "west": ("move_left", None),
    "right": ("move_right", None),
    "go right": ("move_right", None),
    "move right": ("move_right", None),
    "east": ("move_right", None),
    "option a": ("option", "A"),
    "answer a": ("option", "A"),
    "choice a": ("option", "A"),
    "option b": ("option", "B"),
    "answer b": ("option", "B"),
    "choice b": ("option", "B"),
    "option c": ("option", "C"),
    "answer c": ("option", "C"),
    "choice c": ("option", "C"),
    "option d": ("option", "D"),
    "answer d": ("option", "D"),
    "choice d": ("option", "D"),
    "python": ("select_domain", "Python"),
    "sql": ("select_domain", "SQL"),
    "logical reasoning": ("select_domain", "Logical Reasoning"),
    "logic": ("select_domain", "Logical Reasoning"),
    "beginner": ("select_level", "Beginner"),
    "intermediate": ("select_level", "Intermediate"),
    "advanced": ("select_level", "Advanced"),
}
_OPTION_ONLY: dict[str, tuple[str, Optional[str]]] = {
    letter: ("option", letter.upper()) for letter in "abcd"
}
_FILLER_WORDS = {
    "a",
    "an",
    "and",
    "could",
    "for",
    "game",
    "i",
    "just",
    "me",
    "now",
    "please",
    "the",
    "to",
    "want",
    "can",
    "we",
    "will",
    "let",
    "lets",
    "let's",
    "s",
    "like",
    "wanna",
    "would",
    "you",
    "okay",
    "ok",
}
_NEGATION_WORDS = {"don't", "dont", "never", "not", "no", "cannot", "can't"}
_START_WORDS = {"start", "begin", "launch", "enter", "play", "open"}


@dataclass(frozen=True)
class VoiceCommand:
    """A normalized game action and its optional domain, level, or answer value."""

    action: str
    value: Optional[str] = None
    heard: str = ""


def normalize_phrase(phrase: str) -> str:
    """Lowercase a recognized phrase and collapse punctuation and whitespace."""
    normalized = phrase.casefold().replace("’", "'")
    normalized = re.sub(r"[^a-z0-9\s']", " ", normalized)
    return " ".join(normalized.split())


def parse_command(
    phrase: str,
    context: Optional[str] = None,
    threshold: float = config.VOICE["fuzzy_match_threshold"],
) -> Optional[VoiceCommand]:
    """Parse common game phrases, optionally treating unknown text as an answer."""
    normalized = normalize_phrase(phrase)
    if not normalized:
        return None

    if context != "answer" and _has_negated_command(normalized):
        return VoiceCommand("cancel", None, normalized)

    if context == "answer":
        if _has_negated_command(normalized):
            return VoiceCommand("answer_text", normalized, normalized)
        command = _COMMANDS.get(normalized) or _OPTION_ONLY.get(normalized)
        if command is not None and command[0] == "option":
            return VoiceCommand(command[0], command[1], normalized)
        semantic = _semantic_command(normalized)
        if semantic is not None and semantic[0] == "option":
            return VoiceCommand(semantic[0], semantic[1], normalized)
        return VoiceCommand("answer_text", normalized, normalized)

    if context in {"notes", "notes_final"}:
        contextual = _notes_command(normalized, context)
        if contextual is not None:
            return VoiceCommand(contextual[0], contextual[1], normalized)

    command = _COMMANDS.get(normalized) or _OPTION_ONLY.get(normalized)
    if command is not None:
        return VoiceCommand(command[0], command[1], normalized)

    match = _semantic_command(normalized)
    if match is not None:
        return VoiceCommand(match[0], match[1], normalized)

    match = _fuzzy_command(normalized, threshold)
    if match is not None:
        return VoiceCommand(match[0], match[1], normalized)

    return None


def _has_negated_command(phrase: str) -> bool:
    """Reject commands explicitly preceded by a spoken negation."""
    words = phrase.split()
    command_words = (
        _START_WORDS
        | {
            "go",
            "continue",
            "proceed",
            "next",
            "back",
            "previous",
            "quit",
            "exit",
            "leave",
            "up",
            "down",
            "left",
            "right",
            "python",
            "sql",
            "logic",
            "beginner",
            "intermediate",
            "advanced",
            "choose",
            "select",
            "pick",
            "option",
            "choice",
            "answer",
            "a",
            "b",
            "c",
            "d",
        }
    )
    for index, word in enumerate(words):
        if word in _NEGATION_WORDS or (
            word == "do" and index + 1 < len(words) and words[index + 1] == "not"
        ):
            start = index + 1
            if word == "do":
                start += 1
            if any(next_word in command_words for next_word in words[start : start + 5]):
                return True
    return False


def _notes_command(
    phrase: str,
    context: str,
) -> Optional[tuple[str, Optional[str]]]:
    """Interpret short proceed phrases according to the current notes page."""
    words = set(phrase.split())
    starts_maze = bool(words & _START_WORDS) or (
        words & {"maze", "labyrinth"}
        and words & {"go", "continue", "proceed", "resume"}
    )
    if starts_maze:
        return ("start_maze", None)

    if words & {"next", "page", "topic"}:
        if words & {"back", "previous", "prior"}:
            return ("back", None)
        return ("next", None)

    continuation = bool(words & {"continue", "proceed", "advance"}) or (
        {"go", "on"}.issubset(words)
    ) or ({"go", "ahead"}.issubset(words)) or (
        {"let's", "go"}.issubset(words)
    )
    if "ready" in words:
        return ("start_maze", None)
    if continuation:
        return ("start_maze", None) if context == "notes_final" else ("next", None)
    return None


class CommandParser:
    """Apply a cooldown to parsed actions to prevent repeated game input."""

    def __init__(
        self,
        cooldown_seconds: float = config.TIMINGS["command_cooldown_seconds"],
        threshold: float = config.VOICE["fuzzy_match_threshold"],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Configure command matching and a clock suitable for deterministic tests."""
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self.threshold = threshold
        self._clock = clock
        self._last_accepted_at: dict[tuple[str, Optional[str]], float] = {}
        self.was_suppressed = False

    def parse(
        self,
        phrase: str,
        context: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Optional[VoiceCommand]:
        """Parse one phrase and suppress valid commands within the cooldown."""
        self.was_suppressed = False
        command = parse_command(phrase, context=context, threshold=self.threshold)
        if command is None:
            return None
        current_time = self._clock() if now is None else now
        command_key = (command.action, command.value)
        last_accepted_at = self._last_accepted_at.get(command_key)
        if (
            last_accepted_at is not None
            and current_time - last_accepted_at < self.cooldown_seconds
        ):
            self.was_suppressed = True
            return None
        self._last_accepted_at[command_key] = current_time
        return command


def _fuzzy_command(
    phrase: str,
    threshold: float,
) -> Optional[tuple[str, Optional[str]]]:
    """Match short near-miss commands without guessing from long sentences."""
    words = phrase.split()
    if len(phrase) < 3 or len(words) > 2:
        return None
    candidates: dict[tuple[str, Optional[str]], float] = {}
    for candidate, command in _COMMANDS.items():
        candidate_word_count = len(candidate.split())
        if candidate_word_count != len(words) and not (
            candidate_word_count == 1 and len(words) == 2
        ):
            continue
        comparison_phrase = phrase if candidate_word_count == len(words) else "".join(words)
        score = SequenceMatcher(None, comparison_phrase, candidate.replace(" ", "")).ratio()
        candidates[command] = max(score, candidates.get(command, 0.0))
    ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    if ranked and ranked[0][1] >= threshold:
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        if ranked[0][1] - runner_up_score >= 0.08:
            return ranked[0][0]
    return None


def _semantic_command(phrase: str) -> Optional[tuple[str, Optional[str]]]:
    """Recognize the intent in natural phrases, not only exact command wording."""
    words = set(phrase.split())
    meaningful = words - _FILLER_WORDS

    if words & {"quit", "exit", "leave", "close"}:
        return ("quit", None)
    if (
        "help" in words
        or "instruction" in words
        or "instructions" in words
        or {"how", "play"}.issubset(words)
        or {"how", "work"}.issubset(words)
        or (
            "how" in words
            and words & {"start", "begin", "play", "playing", "launch"}
        )
    ):
        return ("how_to_play", None)

    if words & {"maze", "labyrinth"} and words & {
        "back",
        "return",
        "resume",
    }:
        return ("return_to_maze", None)
    if words & {"maze", "labyrinth"} and words & {
        "start",
        "begin",
        "enter",
        "go",
        "play",
        "open",
        "launch",
        "continue",
        "resume",
    }:
        return ("start_maze", None)
    if words & {"replay", "restart"} or (
        words & {"play", "start", "begin"}
        and words & {"again", "restart", "replay"}
    ):
        return ("play_again", None)
    if words & {"retry", "retrying", "retake", "redo", "repeat"} or (
        words & {"try", "attempt"}
        and words & {"again", "once", "another"}
    ):
        return ("retry", None)
    if words & {"menu", "home"} and words & {
        "main",
        "back",
        "return",
        "go",
        "take",
    }:
        return ("main_menu", None)
    if words & {"results", "result", "score", "scores"} and words & {
        "show",
        "view",
        "see",
        "open",
        "display",
        "get",
    }:
        return ("results", None)
    if (
        {"go", "on"}.issubset(words)
        or {"go", "ahead"}.issubset(words)
        or {"let's", "go"}.issubset(words)
    ):
        return ("start", None)

    domain_terms = {
        "python": ("select_domain", "Python"),
        "sql": ("select_domain", "SQL"),
        "sequel": ("select_domain", "SQL"),
        "logic": ("select_domain", "Logical Reasoning"),
        "reasoning": ("select_domain", "Logical Reasoning"),
    }
    for term, command in domain_terms.items():
        if term in meaningful:
            return command
    if {"logical", "reasoning"}.issubset(words):
        return ("select_domain", "Logical Reasoning")

    level_terms = {
        "beginner": ("select_level", "Beginner"),
        "basic": ("select_level", "Beginner"),
        "easy": ("select_level", "Beginner"),
        "easiest": ("select_level", "Beginner"),
        "easier": ("select_level", "Beginner"),
        "starter": ("select_level", "Beginner"),
        "introductory": ("select_level", "Beginner"),
        "intermediate": ("select_level", "Intermediate"),
        "intermediary": ("select_level", "Intermediate"),
        "medium": ("select_level", "Intermediate"),
        "moderate": ("select_level", "Intermediate"),
        "normal": ("select_level", "Intermediate"),
        "advanced": ("select_level", "Advanced"),
        "expert": ("select_level", "Advanced"),
        "hard": ("select_level", "Advanced"),
        "hardest": ("select_level", "Advanced"),
        "challenging": ("select_level", "Advanced"),
    }
    for term, command in level_terms.items():
        if term in meaningful:
            return command

    direction_terms = {
        "up": "move_up",
        "upward": "move_up",
        "forward": "move_up",
        "north": "move_up",
        "down": "move_down",
        "downward": "move_down",
        "backward": "move_down",
        "south": "move_down",
        "left": "move_left",
        "leftward": "move_left",
        "west": "move_left",
        "right": "move_right",
        "rightward": "move_right",
        "east": "move_right",
    }
    directions = {direction_terms[word] for word in words if word in direction_terms}
    movement_cues = words & {
        "go",
        "move",
        "walk",
        "step",
        "head",
        "travel",
        "turn",
        "take",
    }
    if len(directions) == 1 and (movement_cues or len(meaningful) == 1):
        return (next(iter(directions)), None)

    if words & {"next", "forward", "continue", "advance"}:
        return ("next", None)
    if words & {"back", "previous", "prior"}:
        return ("back", None)

    option_words = words & {"option", "answer", "choice"}
    choice_words = option_words | (words & {"choose", "select", "pick"})
    if choice_words:
        ordinal_letters = {
            "first": "A",
            "1": "A",
            "second": "B",
            "two": "B",
            "2": "B",
            "third": "C",
            "three": "C",
            "3": "C",
            "fourth": "D",
            "four": "D",
            "4": "D",
        }
        for ordinal, letter in ordinal_letters.items():
            if ordinal in words:
                return ("option", letter)
        for letter in "abcd":
            if letter in words or {"option", letter}.issubset(words):
                return ("option", letter.upper())
    if len(meaningful) == 1 and next(iter(meaningful)) in {"a", "b", "c", "d"}:
        return ("option", next(iter(meaningful)).upper())

    start_verbs = words & {
        "start",
        "begin",
        "launch",
        "enter",
        "play",
        "open",
        "beginning",
    }
    if start_verbs and words & {
        "learning",
        "game",
        "adventure",
        "voice",
        "maze",
        "session",
        "playing",
    }:
        return ("start", None)
    if words & {"go", "take", "open", "launch"} and words & {
        "game",
        "adventure",
        "learning",
    }:
        return ("start", None)
    if len(meaningful) == 1 and start_verbs:
        return ("start", None)
    return None
