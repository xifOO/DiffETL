from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Self

from diffetl.transform._enum import IssueState
from diffetl.transform.commit import Author
from diffetl.transform.common import parse_dt, parse_dt_opt


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
            number=value["number"],
            title=value["title"],
            description=value.get("bodyText", ""),
            state=IssueState.from_issue_data(value),
            created_at=parse_dt(value["createdAt"]),
            closed_at=parse_dt_opt(value.get("closedAt")),
            author=Author.from_dict(value)
        )
