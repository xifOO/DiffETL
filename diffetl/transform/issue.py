from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Self

from diffetl.transform._enum import IssueState
from diffetl.transform.commit import Author


@dataclass(frozen=True)
class IssueElement:
    number: int
    title: str
    description: Optional[str]
    state: IssueState
    created_at: datetime
    closed_at: Optional[datetime]
    author: Author

    @classmethod
    def from_dict(cls, value: dict) -> Self:
        return cls(
            number=value.get("number", 0),
            title=value.get("title", ""),
            description=value.get("body"),
            state=IssueState.from_issue_data(value),
            created_at=datetime.fromisoformat(
                value["created_at"].replace("Z", "+00:00")
            ),
            closed_at=datetime.fromisoformat(value["closed_at"].replace("Z", "+00:00"))
            if value.get("closed_at")
            else None,
            author=Author(
                name=value["user"]["login"],
                email=None,
            ),
        )
