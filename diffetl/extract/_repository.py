from abc import ABC, abstractmethod
from typing import Dict, List

from git import Commit as GitCommit

from diffetl.extract._client import GitClient
from diffetl.transform.commit import CommitElement


class GitRepository(ABC):
    def __init__(self, git_client: GitClient):
        self.git_client = git_client
    
    @abstractmethod
    def fetch_commits(self, max_count: int, branch: str) -> Dict[str, CommitElement]: ...

    @abstractmethod
    def _create_linked_elements(self, raw_commits: List[GitCommit]) -> List[CommitElement]: ...






