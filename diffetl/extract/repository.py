from diffetl.extract._repository import GitClient
from diffetl.config import save_repo_dir
from git import Repo


class GitHubClient(GitClient):
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self._cloned = False
        self.repo = None

    def _clone(self):
        self.repo = Repo.clone_from(self.repo_url, save_repo_dir)
    
    
