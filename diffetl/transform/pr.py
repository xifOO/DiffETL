from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Self

from diffetl.transform._enum import PullRequestReviewState, PullRequestState
from diffetl.transform.commit import Author
from diffetl.transform.common import parse_dt, parse_dt_opt


@dataclass(frozen=True)
class PullRequestRef:
    number: int
    source_repo: Optional[str]
    target_repo: str
    is_fork: bool

    @classmethod
    def from_pr_data(cls, value: dict) -> Self:
        head_repo = value.get("headRepository")
        source_repo = head_repo["nameWithOwner"] if head_repo is not None else None
        target_repo = value["baseRepository"]["nameWithOwner"]
        return cls(
            number=value["number"],
            source_repo=source_repo,
            target_repo=target_repo,
            is_fork=source_repo != target_repo,
        )
    

@dataclass
class PullRequestReview:
    review_id: str
    author: Author
    body: str
    created_at: datetime
    state: PullRequestReviewState

    @classmethod
    def from_dict(cls, value: dict) -> Self:
        return cls(
            review_id=value["id"],
            author=Author.from_dict(value),
            body=value["bodyText"],
            created_at=parse_dt(value["createdAt"]),
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
            title=value["title"],
            reviews=[
                PullRequestReview.from_dict(r)
                for r in value["reviews"].get("nodes")
            ],
            description=value.get("bodyText"),
            state=PullRequestState.from_pr_data(value),
            created_at=parse_dt(value["createdAt"]),
            merged_at=parse_dt_opt(value.get("mergedAt")),
            closed_at=parse_dt_opt(value.get("closedAt")),
            author=Author.from_dict(value),
            target_branch=value["baseRefName"],
            source_branch=value["headRefName"],
        )
