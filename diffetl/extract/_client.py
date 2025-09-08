from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from git import Commit as GitCommit


class GitClient(ABC):
    @abstractmethod
    def __init__(self, repo_url: str):
        self.repo_url = repo_url

    @abstractmethod
    def _clone(self): ...

    @abstractmethod
    def list_commits(
        self, batch_size: int, branch: str, **kwargs
    ) -> Tuple[List[GitCommit], Optional[str]]: ...
