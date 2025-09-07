import re
from typing import TypedDict, Union

_CONVENTIONAL_COMMIT_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "test",
    "perf",
    "build",
    "ci",
    "chore",
    "revert",
]
_FORBIDDEN_WORDS = ["WIP", "TODO", "FIXME", "TEMP", "DEBUG", "HACK", "XXX"]


class ValidationResult(TypedDict):
    message_is_not_empty: bool
    message_is_conventional: bool
    message_is_within_length: bool
    message_has_forbidden_words: bool


class MessageQualityAssessor:
    def __init__(self, max_length_commit: int = 72):
        self._commit_pattern = re.compile(
            r"^(" + "|".join(_CONVENTIONAL_COMMIT_TYPES) + r")"
            r"(\([a-zA-Z0-9\-_]+\))?"
            r"!?:"
            r"\s+"
            r".+",
            re.IGNORECASE,
        )

        self._forbidden_pattern = re.compile(
            r"\b(" + "|".join(_FORBIDDEN_WORDS) + r")\b", re.IGNORECASE
        )
        self._max_length_commit = max_length_commit

    def validate_message(
        self, message: Union[str, bytes, bytearray, memoryview]
    ) -> ValidationResult:
        if isinstance(message, (bytes, bytearray, memoryview)):
            if isinstance(message, memoryview):
                message = message.tobytes().decode("utf-8")
            else:
                message = message.decode("utf-8")

        is_not_empty = bool(message and not message.isspace())
        is_conventional = (
            bool(self._commit_pattern.match(message.strip())) if is_not_empty else False
        )
        is_within_length = (
            len(message) <= self._max_length_commit if is_not_empty else False
        )
        has_forbidden_words = (
            bool(self._forbidden_pattern.search(message)) if is_not_empty else False
        )

        validation_result: ValidationResult = {
            "message_is_not_empty": is_not_empty,
            "message_is_conventional": is_conventional,
            "message_is_within_length": is_within_length,
            "message_has_forbidden_words": has_forbidden_words,
        }

        return validation_result
