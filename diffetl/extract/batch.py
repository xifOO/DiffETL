from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from git import Commit as GitCommit

from diffetl.extract._raw import ExtractMetadata, RawCommit, SourceInfo


@dataclass
class RawCommitsBatch:
    load_id: UUID
    load_timestamp: datetime
    source_info: SourceInfo
    raw_commits: List[RawCommit] = field(default_factory=list)

    status: str = "loading"
    error: Optional[str] = None

    def add_commits(self, git_commits: List[GitCommit]):
        for gc in git_commits:
            raw_commit = RawCommit(
                git_commit=gc,
                extract_metadata=ExtractMetadata(
                    batch_id=self.load_id, load_timestamp=self.load_timestamp
                ),
            )
            self.raw_commits.append(raw_commit)

    def validate(self, expected: int, actual: int):
        if expected != actual:
            self.mark_failed(f"Expected {expected}, got {actual}")
        else:
            self.status = "success"

    def mark_failed(self, error: str):
        self.error = error
        self.status = "failed"
