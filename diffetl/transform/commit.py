from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, List, Optional, Self, Sequence, TYPE_CHECKING
from git import Commit as GitCommit
if TYPE_CHECKING:
    from diffetl.transform.diff import Diff


@dataclass(frozen=True)
class Author:
    name: str | None
    email: str | None


@dataclass(frozen=True)
class Commit:
    hexsha: str
    message: str
    author: Author
    created_at: datetime
    parents_hexsha: Sequence[str]

    @classmethod
    def from_git_commit(cls, git_commit: GitCommit) -> Self:
        return cls(
            hexsha=git_commit.hexsha,
            message=str(git_commit.message).strip(),
            author=Author(
                name=git_commit.author.name,
                email=git_commit.author.email
            ),
            created_at=datetime.fromtimestamp(git_commit.committed_date, UTC),
            parents_hexsha=[p.hexsha for p in git_commit.parents]
        )


@dataclass(frozen=True)
class CommitElement:
    commit: Commit
    diff: Optional['Diff'] = None

    def __hash__(self) -> int:
        return hash(self.commit.hexsha)
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, CommitElement):
            return self.commit.hexsha == value.commit.hexsha
        return False
    
    def iter_parents(self, commit_map: Dict[str, 'CommitElement']) -> Iterator['CommitElement']:
        for parent_hash in self.commit.parents_hexsha:
            parent_element = commit_map.get(parent_hash)
            if parent_element:
                yield parent_element
    
    @classmethod
    def to_group_dict(cls, elements: List['CommitElement']) -> Dict[str, 'CommitElement']:
        return {ce.hexsha: ce for ce in elements}
    
    @property
    def hexsha(self) -> str:
        return self.commit.hexsha


class CommitGraph:
    def __init__(self, elements: List[CommitElement]) -> None:
        self._commit_map = {e.hexsha: e for e in elements}
    
    def get(self, hexsha: str) -> Optional[CommitElement]:
        return self._commit_map.get(hexsha)
    
    def iter_parents(self, element: CommitElement) -> Iterator[CommitElement]:
        return element.iter_parents(self._commit_map)