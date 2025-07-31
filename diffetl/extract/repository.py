from typing import List
from diffetl.extract._repository import GitClient
from diffetl.config import get_repo_dir
from git import Repo
from git.objects import Commit as GitCommit
from diffetl.transform.commit import Commit


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
    
    def list_commits(self, count: int) -> List[Commit]:
        self._clone()
        if not self.repo:
            raise RuntimeError("Init repo failed.")

        git_commits: List[GitCommit] = list(self.repo.iter_commits("master", max_count=count))
        return [Commit.from_git_commit(gc) for gc in git_commits]


    

