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
    def fetch_all(
        cls,
        client: APIClient,
        *,
        elements_first: int = 50,
        comments_first: int = 20,
    ) -> "BaseCollection[T]":
        collection = cls()

        raw_data = collection._fetch_raw_data(
            client,
            elements_first=elements_first,
            comments_first=comments_first,
        )

        for raw in raw_data:
            element = cls._element_class.from_dict(raw)
            collection._elements.append(element)

        return collection

    @abstractmethod
    def _fetch_raw_data(
        self,
        client: APIClient,
        *,
        elements_first: int,
        comments_first: int,
    ) -> Iterator[dict]: ...


class PullRequestCollection(BaseCollection[PullRequestElement]):
    _element_class = PullRequestElement

    def _fetch_raw_data(
        self, client: APIClient, *, elements_first: int, comments_first: int
    ) -> Iterator[dict]:
        return client.fetch_pull_requests(elements_first, comments_first)


class IssueCollection(BaseCollection[IssueElement]):
    _element_class = IssueElement

    def _fetch_raw_data(
        self, client: APIClient, *, elements_first: int, comments_first: int
    ) -> Iterator[dict]:
        return client.fetch_issues(elements_first, comments_first)
