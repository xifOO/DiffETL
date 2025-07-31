from abc import ABC, abstractmethod
from typing import List

from diffetl.transform.commit import Commit


class GitClient(ABC):
    def __init__(self, repo_url: str): ...

    @abstractmethod
    def _clone(self): ...

    @abstractmethod
    def list_commits(self, count: int) -> List[Commit]: ...
    

class GitRepository(ABC):
    def __init__(self, git_client: GitClient):
        self.git_client = git_client
    
    @abstractmethod
    def fetch_commits(self, max_count: int) -> List[Commit]: ...






