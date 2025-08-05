from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Self, Sequence, Union
from git import Diff as GitDiff, Commit as GitCommit

from diffetl.transform._enum import ChangeType, DiffType, FileType
from diffetl.transform.file import FileMetadata


@dataclass(frozen=True)
class DiffStats:
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    hunks_count: int = 0


@dataclass
class DiffMetadata:
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
        metadata: Optional[FileMetadata] = None,
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
    
    @classmethod
    def to_diff(cls, git_commit: GitCommit) -> Self:
        diff = cls(commit_hexsha=git_commit.hexsha)
        diff._create_metadata(git_commit)
        
        file_elements = diff._load_diff_elements(git_commit)

        for elem in file_elements:
            if elem is not None:
                diff.add_element(elem)
        
        return diff

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
    
    def _create_metadata(self, git_commit: GitCommit) -> None:
        self.metadata = DiffMetadata(
            branch=None,
            tags=[],
            custom_attributes={}
        ) # next time
    
    def _load_diff_elements(self, git_commit: GitCommit) -> List[DiffElement]:
        file_elements = []
        if git_commit.parents:
            parent = git_commit.parents[0]
            git_diff = parent.diff(git_commit)
        else:
            git_diff = git_commit.diff(None)
        
        for diff_item in git_diff:
            file_element = self._create_file_element(diff_item)
            file_elements.append(file_element)
        return file_elements
    
    def _create_file_element(self, diff_item: GitDiff) -> Optional[DiffElement]:
        try:
            if diff_item.new_file:
                change_type = ChangeType.ADDED
                file_path = diff_item.b_path
            elif diff_item.deleted_file:
                change_type = ChangeType.REMOVED
                file_path = diff_item.a_path
            elif diff_item.renamed_file:
                change_type = ChangeType.RENAMED
                file_path = f"{diff_item.a_path} -> {diff_item.b_path}"
            else:
                change_type = ChangeType.MODIFIED
                file_path = diff_item.a_path or diff_item.b_path

            file_type = FileType.from_path_to_content(file_path)
    
            lines_added, lines_removed = self._calculate_lines_stats(diff_item)

            file_stats = DiffStats(
                lines_added=lines_added,
                lines_removed=lines_removed,
                files_changed=1,
                hunks_count=1 if lines_added > 0 or lines_removed > 0 else 0
            )

            file_metadata = FileMetadata(
                mode=str(diff_item.b_mode) if diff_item.b_mode else None,
                is_binary=self._is_binary_file(diff_item),
                type=file_type
            )   

            file_element = DiffElement(
                element_type=DiffType.FILE,
                stats=file_stats,
                identifier=file_path if file_path else "",
                change_type=change_type,
                metadata=file_metadata
            )

            return file_element
        
        except Exception as e:
            return None

    def _calculate_lines_stats(self, diff_item) -> tuple[int, int]:
        lines_added = 0
        lines_removed = 0
        
        try:
            if hasattr(diff_item, 'diff') and diff_item.diff:
                diff_text = diff_item.diff.decode('utf-8', errors='ignore')
                for line in diff_text.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        lines_added += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        lines_removed += 1
        except Exception:
            pass 
        
        return lines_added, lines_removed
    
    def _is_binary_file(self, diff_item) -> bool:
        try:
            if hasattr(diff_item, 'diff') and diff_item.diff:
                return b'\x00' in diff_item.diff[:1024] 
            return False
        except Exception:
            return False

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