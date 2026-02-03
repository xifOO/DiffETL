import mimetypes
import re
from enum import Enum
from functools import lru_cache
from typing import Dict, Final, List, Optional

from git import Commit as GitCommit

_CONFIG_EXTS: Final = (
    ".yaml",
    ".ini",
    ".json",
    ".toml",
    ".yml",
    ".cfg",
    ".conf",
    ".properties",
    ".gitignore",
    ".env",
    ".dockerignore",
)
_TEST_PATHS: Final = ("/test/", "/tests/")
_TEST_PREFIXES: Final = ("tests", "test_")
_TEST_SUFFIXES: Final = ("_test.py", ".spec.ts", "-test.js", ".test.js", "_test.rb")
_DOC_PATHS: Final = ("/docs/", "/doc/", "/documentation/")
_DOC_PREFIXES: Final = ("docs/", "documentation/")
_DOC_SUFFIXES: Final = (".md", ".rst", ".txt")
_DOC_FILES: Final = ("license", "readme", "changelog", "contributing")
_BUILD_PATHS: Final = ("/build/", "/ci/", "/.github/")
_BUILD_FILES: Final = ("makefile", "dockerfile", "docker", ".sh", ".bat", ".ps1")

_SOURCE_CODE_MIMES: Final = {
    "text/x-python",
    "text/javascript",
    "text/x-java-source",
    "text/x-c",
    "text/x-c++",
    "text/x-go",
    "text/x-php",
    "text/x-ruby",
    "text/html",
    "text/css",
}

_CONFIG_MIME_KEYWORDS: Final = ["json", "xml", "yaml", "ini"]
_ARCHIVE_MIME_KEYWORDS: Final = ["zip", "tar", "gzip", "rar", "x-bzip2"]
_BUILD_MIME_KEYWORDS: Final = [
    "application/x-sh",
    "application/x-executable",
    "application/octet-stream",
]

_TEST_BRANCH_NAMES: Final = ("tmp/", "temp/", "wip/", "experiment/", "exp/")
_FIX_BRANCH_NAMES: Final = ("bugfix", "fix", "hotfix")
_FEAT_BRANCH_NAMES: Final = ("feature", "feat")
_DEV_BRANCH_NAMES: Final = ("dev", "develop", "development")
_MAIN_BRANCH_NAMES: Final = ("main", "master", "prod", "production")
_LOST_BRANCH_NAMES: Final = ("zombie", "lost", "abandoned", "ghost")


class DiffType(Enum):
    COMMIT = "commit"
    FILE = "file"
    HUNK = "hunk"
    LINE_GROUP = "line_group"


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    COPIED = "copied"
    TYPE_CHANGED = "type_changed"
    UNCHANGED = "unchanged"

    @classmethod
    def from_git_flag(cls, flag: str) -> Optional["ChangeType"]:
        mapping = {
            "A": cls.ADDED,
            "D": cls.REMOVED,
            "M": cls.MODIFIED,
            "R": cls.RENAMED,
            "C": cls.COPIED,
            "T": cls.TYPE_CHANGED,
            "U": cls.UNCHANGED,
        }
        return mapping.get(flag.upper(), None)


class FileType(Enum):
    SOURCE_CODE = "source_code"
    TEST = "test"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    BUILD = "build"
    DATA = "data"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"

    @classmethod
    @lru_cache(maxsize=1024)
    def from_path_to_content(cls, file_path: Optional[str]) -> "FileType":
        if not file_path:
            return cls.UNKNOWN

        path_lower = file_path.lower()

        if cls._is_test_file(path_lower):
            return cls.TEST
        if cls._is_documentation(path_lower):
            return cls.DOCUMENTATION
        if cls._is_build_file(path_lower):
            return cls.BUILD
        if cls._is_config_file(path_lower):
            return cls.CONFIG
        if cls._is_data_file(path_lower):
            return cls.DATA

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return cls._from_mime_type(mime_type, path_lower)

        return cls.UNKNOWN

    @classmethod
    def _is_test_file(cls, path: str) -> bool:
        return (
            any(p in path for p in _TEST_PATHS)
            or any(path.startswith(prefix) for prefix in _TEST_PREFIXES)
            or path.endswith(_TEST_SUFFIXES)
        )

    @classmethod
    def _is_documentation(cls, path: str) -> bool:
        return (
            any(p in path for p in _DOC_PATHS)
            or any(path.startswith(prefix) for prefix in _DOC_PREFIXES)
            or path.endswith(_DOC_SUFFIXES)
            or any(path.endswith(f) for f in _DOC_FILES)
        )

    @classmethod
    def _is_build_file(cls, path: str) -> bool:
        return any(p in path for p in _BUILD_PATHS) or any(
            f in path for f in _BUILD_FILES
        )

    @classmethod
    def _is_config_file(cls, path: str) -> bool:
        return path.endswith(_CONFIG_EXTS)

    @classmethod
    def _is_data_file(cls, path: str) -> bool:
        return "/data/" in path or path.startswith("data/")

    @classmethod
    def _from_mime_type(cls, mime_type: str, path: str) -> "FileType":
        if mime_type.startswith("text/"):
            if mime_type in _SOURCE_CODE_MIMES:
                return cls.SOURCE_CODE
            if any(ext in mime_type for ext in _CONFIG_MIME_KEYWORDS):
                return cls.CONFIG
            return cls.DATA

        elif mime_type.startswith("application/"):
            if any(ext in mime_type for ext in _CONFIG_MIME_KEYWORDS):
                return cls.CONFIG
            if any(ext in mime_type for ext in _ARCHIVE_MIME_KEYWORDS):
                return cls.ARCHIVE
            if mime_type in _BUILD_MIME_KEYWORDS:
                return cls.BUILD
            return cls.SOURCE_CODE

        elif mime_type.startswith("image/"):
            return cls.IMAGE
        elif mime_type.startswith("audio/"):
            return cls.AUDIO
        elif mime_type.startswith("video/"):
            return cls.VIDEO

        return cls.UNKNOWN


class BranchType(Enum):
    MAIN = "main"
    DEVELOPMENT = "development"
    FEATURE = "feature"
    FIX = "fix"
    RELEASE = "release"
    TEST = "test"
    DEPENDABOT = "dependabot"
    RENOVATE = "renovate"
    SEMAPHORE = "semaphore"
    GITHUB_ACTIONS = "github_actions"
    LOST = "lost"
    OTHER = "other"

    @classmethod
    @lru_cache(maxsize=128)
    def from_branch_name(cls, branch_name: str) -> "BranchType":
        name = branch_name.strip().lower()

        if name in _MAIN_BRANCH_NAMES:
            return cls.MAIN
        elif name in _DEV_BRANCH_NAMES:
            return cls.DEVELOPMENT

        if name.startswith(_FEAT_BRANCH_NAMES):
            return cls.FEATURE

        if name.startswith(_FIX_BRANCH_NAMES):
            return cls.FIX

        if name.startswith("release"):
            return cls.RELEASE

        if name.startswith(_TEST_BRANCH_NAMES):
            return cls.TEST

        if name.startswith("dependabot/"):
            return cls.DEPENDABOT
        elif name.startswith("renovate/"):
            return cls.RENOVATE
        elif name.startswith("semaphore/"):
            return cls.SEMAPHORE
        elif name.startswith("github-actions/"):
            return cls.GITHUB_ACTIONS

        if any(lost_word in name for lost_word in _LOST_BRANCH_NAMES):
            return cls.LOST

        return cls.OTHER


class BotType(Enum):
    DEPENDABOT = "dependabot"
    RENOVATE = "renovate"
    GITHUB_ACTIONS = "github_actions"
    SEMAPHORE = "semaphore"
    PRE_COMMIT_CI = "pre-commit-ci"
    RULTOR = "rultor"

    @classmethod
    def _get_patterns(cls) -> Dict["BotType", List[re.Pattern]]:
        return {
            cls.DEPENDABOT: [
                re.compile(r"dependabot(\[bot\])?"),
                re.compile(r"dependabot@"),
            ],
            cls.RENOVATE: [re.compile(r"renovate"), re.compile(r"renovate-bot@")],
            cls.GITHUB_ACTIONS: [
                re.compile(r"github-actions"),
                re.compile(r"actions@github.com"),
            ],
            cls.SEMAPHORE: [re.compile(r"semaphore"), re.compile(r"semaphoreci@")],
            cls.PRE_COMMIT_CI: [re.compile(r"pre\-commit\-ci\[bot\]")],
            cls.RULTOR: [re.compile(r"@rultor\.com$"), re.compile(r"^rultor@")],
        }

    @classmethod
    def detect(cls, commit: GitCommit) -> Optional["BotType"]:
        name = (commit.author.name or "").lower()
        email = (commit.author.email or "").lower()

        patterns = cls._get_patterns()

        for bot_type, regex_list in patterns.items():
            if any(
                re.search(pattern, name) or re.search(pattern, email)
                for pattern in regex_list
            ):
                return bot_type

        return None


class PRState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"
    DRAFT = "draft"

    @classmethod
    def from_pr_data(cls, pr_data: dict) -> "PRState":
        if pr_data.get("draft", False):
            return cls.DRAFT
        elif pr_data.get("merged_at") is not None:
            return cls.MERGED
        elif pr_data.get("state") == "open":
            return cls.OPEN
        return cls.CLOSED
