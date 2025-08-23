from typing import Dict, List

from git import Commit as GitCommit

from diffetl.extract._client import GitClient
from diffetl.extract._repository import GitRepository
from diffetl.transform.commit import Commit, CommitElement
from diffetl.transform.diff import Diff


class LocalGitRepository(GitRepository):
    def __init__(self, git_client: GitClient):
        self.git_client = git_client
    
    def fetch_commits(self, max_count: int, branch: str) -> Dict[str, CommitElement]: 
        raw_commits: List[GitCommit] = self.git_client.list_commits(max_count, branch)
        elements = self._create_linked_elements(raw_commits)
        return CommitElement.to_group_dict(elements)
    
    def _create_linked_elements(self, raw_commits: List[GitCommit]) -> List[CommitElement]:
        elements: List[CommitElement] = []

        for raw_commit in raw_commits:
            commit = Commit.from_git_commit(raw_commit)
            diff = Diff.to_diff(raw_commit)

            element = CommitElement(
                commit=commit,
                diff=diff
            )

            elements.append(element)
        
        return elements
    