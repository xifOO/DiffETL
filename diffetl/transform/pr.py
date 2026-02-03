from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional, Self, Union, overload

from diffetl.extract.client import APIClient
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
            author=Author(name=value["user"]["login"], email="wedyi28111@gmail.com"),
            target_branch=value["base"]["ref"],
            source_branch=value["head"]["ref"],
        )


class PullRequestCollection:
    def __init__(self) -> None:
        self._elements: List[PullRequestElement] = []
        self._fetched = False

    def _fetch_elements(self, client: APIClient, state: str):
        if not self._fetched:
            for pr_dict in client.fetch_pull_requests(state):
                pr = PullRequestElement.from_dict(pr_dict)
                self._elements.append(pr)
            self._fetched = True

    def __len__(self) -> int:
        return len(self._elements)

    def __iter__(self) -> Iterator[PullRequestElement]:
        return iter(self._elements)

    @overload
    def __getitem__(self, index: int) -> PullRequestElement: ...

    @overload
    def __getitem__(self, index: slice) -> List[PullRequestElement]: ...

    def __getitem__(
        self, index: Union[int, slice]
    ) -> Union[PullRequestElement, List[PullRequestElement]]:
        return self._elements[index]

    @classmethod
    def fetch_all(cls, client: APIClient, state: str = "all") -> Self:
        collection = cls()
        collection._fetch_elements(client, state)
        return collection

    def filter_by_author(self, author_name: str) -> Iterator[PullRequestElement]:
        for pr in self._elements:
            if pr.author.name == author_name:
                yield pr
