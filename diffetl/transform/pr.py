from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Self

from diffetl.transform._enum import PRState
from diffetl.transform.commit import Author


@dataclass(frozen=True)
class PullRequestRef:
    pr_number: int
    source_repo: str
    target_repo: str
    is_fork: bool

    @classmethod
    def from_pr_data(cls, value: dict) -> Self:
        source_repo = value["head"]["repo"]["full_name"]
        target_repo = value["base"]["repo"]["full_name"]

        return cls(
            pr_number=value["number"],
            source_repo=source_repo,
            target_repo=target_repo,
            is_fork=source_repo != target_repo,
        )


@dataclass(frozen=True)
class PullRequestElement:
    ref: PullRequestRef
    title: str
    reviewers: List[str]
    description: Optional[str]
    state: PRState
    created_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    author: Author
    target_branch: str
    source_branch: str

    @classmethod
    def from_dict(cls, value: dict) -> Self:
        print(value["user"])
        return cls(
            ref=PullRequestRef.from_pr_data(value),
            title=value.get("title", ""),
            reviewers=[rew["login"] for rew in value.get("requested_reviewers", [])],
            description=value.get("body"),
            state=PRState.from_pr_data(value),
            created_at=datetime.fromisoformat(
                value["created_at"].replace("Z", "+00:00")
            ),
            merged_at=datetime.fromisoformat(value["merged_at"].replace("Z", "+00:00"))
            if value.get("merged_at")
            else None,
            closed_at=datetime.fromisoformat(value["closed_at"].replace("Z", "+00:00"))
            if value.get("closed_at")
            else None,
            author=Author(name=value["user"]["login"], email=None),
            target_branch=value["base"]["ref"],
            source_branch=value["head"]["ref"],
        )
