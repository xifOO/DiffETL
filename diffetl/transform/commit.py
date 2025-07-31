from collections.abc import Iterator
from dataclasses import dataclass
import datetime
from typing import Dict, List


@dataclass(frozen=True)
class Author:
    name: str
    email: str


@dataclass(frozen=True)
class Commit:
    chash: str
    message: str
    author: Author
    created_at: datetime.datetime
    parent_chash: List[str] 


@dataclass
class CommitElement:
    commit: Commit
    _commit_map: Dict[str, 'CommitElement']

    def __hash__(self) -> int:
        return hash(self.commit.chash)
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, CommitElement):
            return self.commit.chash == value.commit.chash
        return False
    
    def iter_parents(self) -> Iterator['CommitElement']:
        for parent_hash in self.commit.parent_chash:
            parent_element = self._commit_map.get(parent_hash)
            if parent_element:
                yield parent_element
        
    @classmethod
    def from_commits_list(cls, commits_data: List[Commit]) -> Dict[str, 'CommitElement']:
        all_elements: Dict[str, CommitElement] = {}

        for commit_data in commits_data:
            all_elements[commit_data.chash] = cls(
                commit=commit_data,
                _commit_map=all_elements
            )

        return all_elements
    
    @property
    def chash(self) -> str:
        return self.commit.chash
    