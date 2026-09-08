from abc import ABC, abstractmethod
from typing import ClassVar, Generic, Iterator, List, Optional, Type, TypeVar, Union, overload

from diffetl.extract.client import HTTPClient
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
    def stream_batches(
        cls,
        client: HTTPClient,
        *,
        page_size: int = 50,          
        comments_first: int = 20,
        output_batch_size: int = 500, 
        last_cursor: Optional[str] = None,
        **extra_kwargs,        
    ) -> Iterator[List[T]]:
        collection = cls()

        raw_data = collection._fetch_raw_data(
            client,
            page_size=page_size,
            comments_first=comments_first,
            last_cursor=last_cursor,
            **extra_kwargs,
        )

        batch: List[T] = []
        for raw in raw_data:
            batch.append(cls._element_class.from_dict(raw))
            if len(batch) >= output_batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    @abstractmethod
    def _fetch_raw_data(
        self,
        client: HTTPClient,
        *,
        page_size: int,
        comments_first: int,
        last_cursor: Optional[str] = None,
        **extra_kwargs,
    ) -> Iterator[dict]: ...


class PullRequestCollection(BaseCollection[PullRequestElement]):
    _element_class = PullRequestElement

    def _fetch_raw_data(
        self,
        client: HTTPClient,
        *,
        page_size: int,
        comments_first: int,
        last_cursor: Optional[str] = None,
        reviews_first: int = 10,
        **_,
    ) -> Iterator[dict]:
        return client.fetch_pull_requests(
            page_size, reviews_first, comments_first, last_cursor=last_cursor
        )


class IssueCollection(BaseCollection[IssueElement]):
    _element_class = IssueElement

    def _fetch_raw_data(
        self,
        client: HTTPClient,
        *,
        page_size: int,
        comments_first: int,
        last_cursor: Optional[str] = None,
        **_,
    ) -> Iterator[dict]:
        return client.fetch_issues(page_size, comments_first, last_cursor=last_cursor)