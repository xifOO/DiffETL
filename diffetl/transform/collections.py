from abc import ABC, abstractmethod
from typing import ClassVar, Generic, Iterator, List, Type, TypeVar, Union, overload

from diffetl.extract.client import APIClient
from diffetl.transform.issue import IssueElement
from diffetl.transform.pr import PullRequestElement

T = TypeVar("T")


class BaseCollection(Generic[T], ABC):
    _element_class: ClassVar[Type]

    def __init__(self) -> None:
        self._elements: List[T] = []
        self._fetched = False

    def _fetch_elements(self, client: APIClient, state: str) -> None:
        if not self._fetched:
            raw_data = self._fetch_raw_data(client, state)
            for raw in raw_data:
                element = self._element_class.from_dict(raw)
                self._elements.append(element)
            self._fetched = True

    def __len__(self) -> int:
        return len(self._elements)

    def __iter__(self) -> Iterator[T]:
        return iter(self._elements)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> List[T]: ...

    def __getitem__(self, index: Union[int, slice]) -> Union[T, List[T]]:
        return self._elements[index]

    @classmethod
    def fetch_all(cls, client: APIClient, state: str = "all") -> "BaseCollection[T]":
        collection = cls()
        collection._fetch_elements(client, state)
        return collection

    @abstractmethod
    def _fetch_raw_data(self, client: APIClient, state: str) -> Iterator[dict]: ...


class PullRequestCollection(BaseCollection[PullRequestElement]):
    _element_class = PullRequestElement

    def _fetch_raw_data(self, client: APIClient, state: str) -> Iterator[dict]:
        return client.fetch_pull_requests(state)


class IssueCollection(BaseCollection[IssueElement]):
    _element_class = IssueElement

    def _fetch_raw_data(self, client: APIClient, state: str) -> Iterator[dict]:
        return client.fetch_issues(state)
