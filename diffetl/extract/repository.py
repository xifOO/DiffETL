from datetime import datetime
from typing import Optional
from uuid import uuid4

from diffetl.extract.batch import RawCommitsBatch
from diffetl.extract.client import GitClient
from diffetl.extract.raw import SourceInfo


class LocalGitRepository:
    def __init__(self, git_client: GitClient):
        self.git_client = git_client

    def extract_commits_batch(
        self, batch_size: int, branch: str, last_sha: Optional[str] = None
    ):
        raw_commits_batch = RawCommitsBatch(
            load_id=uuid4(),
            load_timestamp=datetime.now(),
            source_info=SourceInfo(repo_url=self.git_client.repo_url, branch=branch),
        )
        try:
            list_raw_commits, new_last_sha = self.git_client.list_commits(
                batch_size, branch, last_sha=last_sha
            )
            raw_commits_batch.add_commits(list_raw_commits)
            raw_commits_batch.validate(
                expected=batch_size, actual=len(list_raw_commits)
            )
            return raw_commits_batch, new_last_sha
        except Exception as e:
            raw_commits_batch.mark_failed(str(e))
            return raw_commits_batch, last_sha
