from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Sequence, Union, overload

from diffetl.transform._enum import ChangeType, DiffType
from diffetl.transform.commit import Author


@dataclass(frozen=True)
class DiffStats:
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    hunks_count: int = 0


@dataclass
class DiffMetadata:
    author: Optional[Author] = None
    timestamp: Optional[datetime] = None
    commit_hexsha: Optional[str] = None
    branch: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


class DiffElement:

    def __init__(
        self,
        element_type: DiffType,
        stats: DiffStats,
        identifier: str,
        change_type: ChangeType = ChangeType.MODIFIED,
        metadata: Optional[DiffMetadata] = None,
        parent: Optional['DiffElement'] = None
    ) -> None:
        self.element_type = element_type
        self.stats = stats
        self.identifier = identifier
        self.change_type = change_type
        self.metadata = metadata
        self.parent = parent
        self._children: List['DiffElement'] = []
    
    @property
    def children(self):
        return self._children.copy()
    
    def add_children(self, child: 'DiffElement'):
        child.parent = self
        self._children.append(child)

    def get_children_by_type(self, element_type: DiffType) -> List['DiffElement']:
        return [child for child in self._children if child.element_type == element_type]


class Diff:

    def __init__(
        self,
        commit_hexsha: str,
        metadata: Optional[DiffMetadata] = None
    ) -> None:
        self.commit_hexsha = commit_hexsha
        self.metadata = metadata
        self._elements: List[DiffElement] = []
    
    def __len__(self) -> int:
        return len(self._elements)
    
    def __iter__(self) -> Iterator[DiffElement]:
        return iter(self._elements)

    def __getitem__(self, index: Union[int, slice]) -> Union[DiffElement, Sequence[DiffElement]]:
        if isinstance(index, slice):
            return self._elements[index]
        return self._elements[index]
    
    def add_element(self, element: DiffElement) -> None:
        self._elements.append(element) 
    
    def walk(self) -> Iterator[DiffElement]:
        for element in self._elements:
            yield from self._walk(element)
    
    def get_root_elements(self) -> List[DiffElement]:
        return self._elements.copy()

    def get_elements_by_type(self, element_type: DiffType) -> List[DiffElement]:
        return [elem for elem in self._elements if elem.element_type == element_type]
    
    def find_element_by_identifier(self, identifier: str) -> Optional[DiffElement]:
        for element in self._elements:
            if element.identifier == identifier:
                return element
            result = self._find_in_children(element, identifier)
            if result:
                return result
        return None
    
    def get_aggregated_stats(self) -> DiffStats:
        total_lines_added = 0 
        total_lines_removed = 0
        total_hunks = 0
        unique_files = set()

        for elem in self.get_elements_by_type(DiffType.FILE):
            unique_files.add(elem.identifier)
            total_lines_added += elem.stats.lines_added
            total_lines_removed += elem.stats.lines_removed
            total_hunks += elem.stats.hunks_count

        return DiffStats(
            lines_added=total_lines_added,
            lines_removed=total_lines_removed,
            files_changed=len(unique_files),
            hunks_count=total_hunks
        )

    def _walk(self, element: DiffElement) -> Iterator[DiffElement]:
        yield element
        for child in element.children:
            yield from self._walk(child)
    
    def _find_in_children(self, element: DiffElement, identifier: str) -> Optional[DiffElement]:
        for child in element.children:
            if child.identifier == identifier:
                return child
            
            result = self._find_in_children(child, identifier)
            if result:
                return result
        return None