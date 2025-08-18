from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Self, Sequence, TYPE_CHECKING
from git import BadName, Commit as GitCommit

from diffetl.transform._enum import BotType, BranchType
if TYPE_CHECKING:
    from diffetl.transform.diff import Diff


@dataclass(frozen=True)
class Author:
    name: str | None
    email: str | None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "name": self.name,
            "email": self.email
        }


class CommitMetadata:
    def __init__(self, git_commit: GitCommit) -> None:
        self.branches: List[str] = self._get_branches(git_commit)
        self.tags: List[str] = self._get_tags(git_commit)
        self.custom_attributes: Dict[str, Any] = {}

        self._add_branch_types()
        self._detect_bot_commit(git_commit)
    
    def add_custom_attribute(self, key: str, value: Any) -> None:
        self.custom_attributes[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "branches": self.branches,
            "tags": self.tags,
            "custom_attributes": self.custom_attributes
        }
    
    def _add_branch_types(self):
        branch_types = [BranchType.from_branch_name(b) for b in self.branches]

        type_counts = {}
        for bt in BranchType:
            count = sum(1 for t in branch_types if t == bt)
            if count > 0:
                type_counts[f"branch_count_{bt.value}"] = count

        self.add_custom_attribute("branch_types", [bt.value for bt in branch_types])
        self.add_custom_attribute("branch_summary", type_counts)
        self.add_custom_attribute("has_lost_branch", BranchType.LOST in branch_types)
    

    def _detect_bot_commit(self, git_commit: GitCommit) -> None:
        is_bot_branch = any(
            t in (BranchType.DEPENDABOT, BranchType.RENOVATE,
                  BranchType.SEMAPHORE, BranchType.GITHUB_ACTIONS)
            for t in [BranchType.from_branch_name(b) for b in self.branches]
        )

        bot_type = BotType.detect(git_commit)

        self.add_custom_attribute("is_bot_related", is_bot_branch or bool(bot_type))
        self.add_custom_attribute("bot_type", bot_type.value if bot_type else None)

    def _get_branches(self, git_commit: GitCommit) -> List[str]:
        try:
            branches = []
            repo = git_commit.repo
            commit_hexsha = git_commit.hexsha

            for head in repo.heads:
                if head.commit.hexsha == commit_hexsha:
                    branches.append(head.name)

            for remote in repo.remotes:
                try:
                    for ref in remote.refs:
                        if ref.name.endswith("/HEAD"):
                            continue
                        if ref.commit.hexsha == commit_hexsha:
                            branch_name = ref.name.split('/', 1)[-1]
                            branches.append(branch_name)
                except (ValueError, BadName):
                    continue

            return list(set(branches))

        except Exception:
            return []


    def _get_tags(self, git_commit: GitCommit):
        try:
            repo = git_commit.repo
            tags = []

            for ref in repo.tags:
                if ref.commit.hexsha == git_commit.hexsha:
                    tags.append(ref.name)
            return tags
        except Exception:
            return []


@dataclass(frozen=True)
class Commit:
    hexsha: str
    message: str
    author: Author
    created_at: datetime
    parents_hexsha: Sequence[str]

    metadata: CommitMetadata

    @classmethod
    def from_git_commit(cls, git_commit: GitCommit) -> Self:
        metadata = CommitMetadata(git_commit)
        return cls(
            hexsha=git_commit.hexsha,
            message=str(git_commit.message).strip(),
            author=Author(
                name=git_commit.author.name,
                email=git_commit.author.email
            ),
            created_at=datetime.fromtimestamp(git_commit.committed_date, UTC),
            parents_hexsha=[p.hexsha for p in git_commit.parents],
            metadata=metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hexsha": self.hexsha,
            "message": self.message,
            "author": self.author.to_dict(),
            "created_at": self.created_at,
            "parents_hexsha": self.parents_hexsha,
            "metadata": self.metadata.to_dict(),
        }


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
    
    def to_dict(self) -> Dict[str, Any]:
        data = self.commit.to_dict()

        data.update({
            "is_bot": self.metadata.custom_attributes.get("is_bot_related", False),
            "branch_types": self.metadata.custom_attributes.get("branch_types", [])
        })
        
        if self.diff:
            stats = self.diff.get_aggregated_stats()

            data.update({
                "files_changed": stats.files_changed,
                "lines_added": stats.lines_added
            })
        return data
    
    @classmethod
    def to_group_dict(cls, elements: List['CommitElement']) -> Dict[str, 'CommitElement']:
        return {ce.hexsha: ce for ce in elements}
    
    @property
    def hexsha(self) -> str:
        return self.commit.hexsha
    
    @property
    def message(self) -> str:
        return self.commit.message
    
    @property
    def metadata(self) -> CommitMetadata:
        return self.commit.metadata


class CommitGraph:
    def __init__(self, elements: List[CommitElement]) -> None:
        self._commit_map = {e.hexsha: e for e in elements}
    
    def get(self, hexsha: str) -> Optional[CommitElement]:
        return self._commit_map.get(hexsha)
    
    def iter_parents(self, element: CommitElement) -> Iterator[CommitElement]:
        return element.iter_parents(self._commit_map)