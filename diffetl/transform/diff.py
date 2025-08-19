from dataclasses import dataclass
from typing import Iterator, List, Optional, Self, Sequence, Union
from git import Diff as GitDiff, Commit as GitCommit

from diffetl.transform._enum import ChangeType, DiffType, FileType
from diffetl.transform.file import FileMetadata
from diffetl.utils import is_binary_file


class DiffStats:

    def __init__(self, diff_item: GitDiff):
        self.lines_added, self.lines_removed = self._calculate_lines_stats(diff_item)
        self.files_changed = 1
        
        is_binary = is_binary_file(diff_item)
        self.hunks_count = 1 if (self.lines_added > 0 or self.lines_removed > 0) and not is_binary else 0

    def _calculate_lines_stats(self, diff_item: GitDiff) -> tuple[int, int]:        
        try:
            if is_binary_file(diff_item):
                return 0, 0 
            
            a_content = diff_item.a_blob.data_stream.read().decode('utf-8', errors='ignore') if diff_item.a_blob else ""
            b_content = diff_item.b_blob.data_stream.read().decode('utf-8', errors='ignore') if diff_item.b_blob else ""

            a_lines = a_content.splitlines() if a_content else []
            b_lines = b_content.splitlines() if b_content else []
            
            if not a_lines: 
                return len(b_lines), 0
            elif not b_lines: 
                return 0, len(a_lines)
            else:
                return max(0, len(b_lines) - len(a_lines)), max(0, len(a_lines) - len(b_lines))
        except Exception: 
            pass 
        return 0, 0


@dataclass
class AggregatedDiffStats:
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    hunks_count: int = 0


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
        commit_hexsha: str
    ) -> None:
        self.commit_hexsha = commit_hexsha
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
    
    def get_aggregated_stats(self) -> AggregatedDiffStats:
        total_lines_added = 0 
        total_lines_removed = 0
        total_hunks = 0
        unique_files = set()

        for elem in self.get_elements_by_type(DiffType.FILE):
            unique_files.add(elem.identifier)
            total_lines_added += elem.stats.lines_added
            total_lines_removed += elem.stats.lines_removed
            total_hunks += elem.stats.hunks_count


        return AggregatedDiffStats(
            lines_added=total_lines_added,
            lines_removed=total_lines_removed,
            files_changed=len(unique_files),
            hunks_count=total_hunks
        )
    
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
            elif diff_item.copied_file:
                change_type = ChangeType.COPIED
                file_path = diff_item.a_path
            else:
                change_type = ChangeType.MODIFIED
                file_path = diff_item.a_path or diff_item.b_path

            file_type = FileType.from_path_to_content(file_path)
            diff_stats = DiffStats(diff_item)

            file_metadata = FileMetadata(
                mode=str(diff_item.b_mode) if diff_item.b_mode else None,
                is_binary=is_binary_file(diff_item),
                type=file_type
            )   

            file_element = DiffElement(
                element_type=DiffType.FILE,
                stats=diff_stats,
                identifier=file_path if file_path else "",
                change_type=change_type,
                metadata=file_metadata
            )

            return file_element
        
        except Exception as e:
            return None

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