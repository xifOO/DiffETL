from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from git import Commit as GitCommit


@dataclass
class SourceInfo:
    repo_url: str
    branch: str


@dataclass
class ExtractMetadata:
    batch_id: UUID
    load_timestamp: datetime


@dataclass
class RawCommit:
    git_commit: GitCommit
    extract_metadata: ExtractMetadata
