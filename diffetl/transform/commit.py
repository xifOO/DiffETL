from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Self, Sequence
from git.objects import Commit as GitCommit


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
            created_at=datetime.fromtimestamp(git_commit.committed_date),
            parents_hexsha=[p.hexsha for p in git_commit.parents]
        )


@dataclass
class CommitElement:
    commit: Commit
    _commit_map: Dict[str, 'CommitElement']

    def __hash__(self) -> int:
        return hash(self.commit.hexsha)
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, CommitElement):
            return self.commit.hexsha == value.commit.hexsha
        return False
    
    def iter_parents(self) -> Iterator['CommitElement']:
        for parent_hash in self.commit.parents_hexsha:
            parent_element = self._commit_map.get(parent_hash)
            if parent_element:
                yield parent_element
        
    @classmethod
    def from_commits_list(cls, commits_data: List[Commit]) -> Dict[str, 'CommitElement']:
        all_elements: Dict[str, CommitElement] = {}

        for commit_data in commits_data:
            all_elements[commit_data.hexsha] = cls(
                commit=commit_data,
                _commit_map=all_elements
            )

        return all_elements
    
    @property
    def hexsha(self) -> str:
        return self.commit.hexsha
    