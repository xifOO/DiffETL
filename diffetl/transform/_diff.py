from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from git import Diff as GitDiff
from git import Commit as GitCommit
from diffetl.transform._enum import ChangeType, DiffType
from diffetl.transform.commit import Author
from diffetl.transform.diff import Diff, DiffElement, DiffMetadata, DiffStats


@dataclass
class _Diff:
    commit_hexsha: str
    git_commit: GitCommit
    metadata: Optional[DiffMetadata] = None

    def to_diff(self) -> Diff:
        if self.metadata is None:
            self._create_metadata()
        
        file_elements = self._load_diff_elements()

        diff = Diff(commit_hexsha=self.commit_hexsha, metadata=self.metadata)
        for elem in file_elements:
            if elem is not None:
                diff.add_element(elem)
        
        return diff

    def _create_metadata(self) -> None:
        self.metadata = DiffMetadata(
            author=Author(
                name=self.git_commit.author.name,
                email=self.git_commit.author.email
            ),
            timestamp=datetime.fromtimestamp(self.git_commit.committed_date),
            commit_hexsha=self.git_commit.hexsha,
            branch=None,
            tags=[],
            custom_attributes={"message": self.git_commit.message.strip()}
        )
    
    def _load_diff_elements(self) -> List[DiffElement]:
        file_elements = []
        if self.git_commit.parents:
            parent = self.git_commit.parents[0]
            git_diff = parent.diff(self.git_commit)
        else:
            git_diff = self.git_commit.diff(None)
        
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

    
            lines_added, lines_removed = self._calculate_lines_stats(diff_item)

            file_stats = DiffStats(
                lines_added=lines_added,
                lines_removed=lines_removed,
                files_changed=1,
                hunks_count=1 if lines_added > 0 or lines_removed > 0 else 0
            )

            file_metadata = DiffMetadata(
                commit_hexsha=self.commit_hexsha,
                custom_attributes={
                    "file_mode": str(diff_item.b_mode) if diff_item.b_mode else None,
                    "is_binary": self._is_binary_file(diff_item)
                }
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



    