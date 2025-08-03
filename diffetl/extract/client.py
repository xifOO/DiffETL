from typing import List
from diffetl.extract._repository import GitClient
from diffetl.config import get_repo_dir
from git import Repo
from git import Commit as GitCommit


class GitHubClient(GitClient):
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self._cloned = False
        self.repo = None

    def _clone(self):
        repo_dir = get_repo_dir(self.repo_url)

        if repo_dir.exists():
            self.repo = Repo(str(repo_dir))
            if not self.repo.is_dirty():
                origin = self.repo.remotes.origin
                origin.pull()
        else:
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            self.repo = Repo.clone_from(self.repo_url, str(repo_dir))
    
    def list_commits(self, count: int, branch: str) -> List[GitCommit]:
        self._clone()
        if not self.repo:
            raise RuntimeError("Init repo failed.")

        git_commits: List[GitCommit] = list(self.repo.iter_commits(branch, max_count=count))
        return git_commits



    

