from abc import ABC, abstractmethod
from typing import List

from git import Commit as GitCommit



class GitClient(ABC):
    def __init__(self, repo_url: str): ...

    @abstractmethod
    def _clone(self): ...

    @abstractmethod
    def list_commits(self, count: int, branch: str) -> List[GitCommit]: ...