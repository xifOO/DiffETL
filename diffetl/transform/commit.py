from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Self, Sequence

from git import Commit as GitCommit

from diffetl.transform._enum import BotType, BranchType
from diffetl.transform.assessor import MessageQualityAssessor

if TYPE_CHECKING:
    from diffetl.transform.diff import Diff


@dataclass(frozen=True)
class Author:
    name: str | None
    email: str | None


class CommitMetadata:
    def __init__(self, git_commit: GitCommit) -> None:
        self._commit: GitCommit = git_commit

        self.branches: List[str] = self._get_branches()
        self.tags: List[str] = self._get_tags()
        self.custom_attributes: Dict[str, Any] = {}

        self._add_branch_types()
        self._detect_bot_commit()
        self._check_quality_message()
    
    def to_dict(self):
        ca = self.custom_attributes

        return {
            "branches": self.branches,
            "tags": self.tags,
            "is_bot": ca.get("is_bot_related", False),
            "bot_type": ca.get("bot_type"),
            "has_lost_branch": ca.get("has_lost_branch", False),
            "branch_types": ca.get("branch_types", []),
            "message_is_not_empty": ca.get("message_is_not_empty", None),
            "message_is_conventional": ca.get("message_is_conventional", None),
            "message_is_within_length": ca.get("message_is_within_length", None),
            "message_has_forbidden_words": ca.get("message_has_forbidden_words", None)
        }
    
    def add_custom_attribute(self, key: str, value: Any) -> None:
        self.custom_attributes[key] = value
    
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
    

    def _detect_bot_commit(self) -> None:
        is_bot_branch = any(
            t in (BranchType.DEPENDABOT, BranchType.RENOVATE,
                  BranchType.SEMAPHORE, BranchType.GITHUB_ACTIONS)
            for t in [BranchType.from_branch_name(b) for b in self.branches]
        )

        bot_type = BotType.detect(self._commit)

        self.add_custom_attribute("is_bot_related", is_bot_branch or bool(bot_type))
        self.add_custom_attribute("bot_type", bot_type.value if bot_type else None)
    
    def _check_quality_message(self) -> None:
        assessor = MessageQualityAssessor()
        validation_result = assessor.validate_message(self._commit.message)
        
        for k, v in validation_result.items():
            self.add_custom_attribute(k, v)


    def _get_branches(self) -> List[str]:
        repo = self._commit.repo
        commit_hexsha = self._commit.hexsha
        
        branches = set()
        
        try:
            if not repo.head.is_detached:
                current_branch = repo.active_branch.name
                if commit_hexsha in [c.hexsha for c in repo.iter_commits(current_branch)]:
                    branches.add(current_branch)
        except Exception:
            return []
        
        try:
            result = repo.git.branch('--contains', commit_hexsha)
            for line in result.split('\n'):
                line = line.strip()
                if line and not line.startswith('* '):
                    branches.add(line)
        except Exception:
            return []
        
        return list(branches) if branches else []
            

    def _get_tags(self) -> List[str]:
        tags = set()
        repo = self._commit.repo
        commit_hexsha = self._commit.hexsha

        try:
            result = repo.git.tag('--points-at', commit_hexsha)
            for tag_name in result.split('\n'):
                tag_name = tag_name.strip()
                if tag_name:
                    tags.add(tag_name)
        except Exception:
            return []
        
        return list(tags) if tags else []


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

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "hexsha": self.hexsha,
            "message": self.message,
            "author_name": self.author.name,
            "author_email": self.author.email,
            "created_at": self.created_at.isoformat(),
            "parents_hexsha": self.parents_hexsha,
            **self.metadata.to_dict()
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
        data = self.commit.to_flat_dict()
        
        if self.diff:
            stats = self.diff.get_aggregated_stats()
            data.update(asdict(stats))

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