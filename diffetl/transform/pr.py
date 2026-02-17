from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Self

from diffetl.transform._enum import PullRequestReviewState, PullRequestState
from diffetl.transform.commit import Author


@dataclass(frozen=True)
class PullRequestRef:
    number: int
    source_repo: str
    target_repo: str
    is_fork: bool

    @classmethod
    def from_pr_data(cls, value: dict) -> Self:
        source_repo = value["headRepository"]["nameWithOwner"]
        target_repo = value["baseRepository"]["nameWithOwner"]
        return cls(
            number=value["number"],
            source_repo=source_repo,
            target_repo=target_repo,
            is_fork=source_repo != target_repo,
        )


@dataclass
class PullRequestReview:
    author: Author
    body: str
    created_at: datetime
    state: PullRequestReviewState

    @classmethod
    def from_dict(cls, value: dict) -> Self:
        return cls(
            author=Author(
                name=value["author"]["login"] if value.get("author") else None,
                email=None,
            ),
            body=value.get("bodyText", ""),
            created_at=datetime.fromisoformat(
                value["createdAt"].replace("Z", "+00:00")
            ),
            state=PullRequestReviewState.from_pr_review_data(value),
        )


@dataclass(frozen=True)
class PullRequestElement:
    ref: PullRequestRef
    title: str
    reviews: List[PullRequestReview]
    description: Optional[str]
    state: PullRequestState
    created_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    author: Author
    target_branch: str
    source_branch: str

    @classmethod
    def from_dict(cls, value: dict) -> Self:
        return cls(
            ref=PullRequestRef.from_pr_data(value),
            title=value.get("title", ""),
            reviews=[
                PullRequestReview.from_dict(r)
                for r in (value.get("reviews") or {}).get("nodes") or []
            ],
            description=value.get("bodyText"),
            state=PullRequestState.from_pr_data(value),
            created_at=datetime.fromisoformat(
                value["createdAt"].replace("Z", "+00:00")
            ),
            merged_at=datetime.fromisoformat(value["mergedAt"].replace("Z", "+00:00"))
            if value.get("mergedAt")
            else None,
            closed_at=datetime.fromisoformat(value["closedAt"].replace("Z", "+00:00"))
            if value.get("closedAt")
            else None,
            author=Author(
                name=value["author"]["login"] if value.get("author") else None,
                email=None,
            ),
            target_branch=value["baseRefName"],
            source_branch=value["headRefName"],
        )
