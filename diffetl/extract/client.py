import urllib.parse
from abc import abstractmethod
from typing import Dict, Iterator, List, Optional, Tuple

import requests
from git import Commit as GitCommit
from git import Repo

from diffetl.config import GITHUB_GRAPHQL, get_repo_dir
from diffetl.extract._client import GitClient
from diffetl.extract.graphql.queries.issue import build_issue_query
from diffetl.extract.graphql.queries.pr import build_pr_query


class LocalGitClient(GitClient):
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self._cloned = False
        self.repo = None

    def _clone(self):
        if not self._cloned:
            repo_dir = get_repo_dir(self.repo_url)

            if repo_dir.exists():
                self.repo = Repo(str(repo_dir))
                if not self.repo.is_dirty():
                    origin = self.repo.remotes.origin
                    origin.pull()
            else:
                repo_dir.parent.mkdir(parents=True, exist_ok=True)
                self.repo = Repo.clone_from(self.repo_url, str(repo_dir))
        self._cloned = True

    def list_commits(
        self, batch_size: int, branch: str, **kwargs
    ) -> Tuple[List[GitCommit], Optional[str]]:
        self._clone()
        if not self.repo:
            raise RuntimeError("Init repo failed.")

        iterator_gc = self.repo.iter_commits(branch)
        batch = []
        last_sha = kwargs.get("last_sha")
        skip = last_sha is not None

        for gc in iterator_gc:
            if skip:
                if gc.hexsha == last_sha:
                    skip = False
                continue
            batch.append(gc)
            if len(batch) == batch_size:
                break

        new_last_sha = batch[-1].hexsha if batch else None
        return batch, new_last_sha


class APIClient:
    def __init__(self, repo_url: str, token: Optional[str] = None) -> None:
        self.token = token
        self.owner, self.repo_name = self._parse_url(repo_url)

    def _parse_url(self, repo_url: str) -> Tuple[str, str]:
        if repo_url.startswith("git@"):
            repo_url = repo_url.replace("git@", "https://").replace(":", "/")

        parsed = urllib.parse.urlparse(repo_url)
        path = parsed.path.strip("/")

        if path.endswith(".git"):
            path = path[:-4]

        parts = [p for p in path.split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Invalid repo URL: {repo_url}")

        return parts[-2], parts[-1]

    @abstractmethod
    def fetch_pull_requests(self) -> Iterator[Dict]: ...

    @abstractmethod
    def fetch_issues(self) -> Iterator[Dict]: ...


class GithubGraphQLClient(APIClient):
    def __init__(self, repo_url: str, token: Optional[str] = None) -> None:
        super().__init__(repo_url, token)
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _query(self, query: str, variables=None):
        resp = self.session.post(
            GITHUB_GRAPHQL, json={"query": query, "variables": variables or {}}
        )
        resp.raise_for_status()
        payload = resp.json()

        if "errors" in payload:
            raise RuntimeError(payload["errors"])

        return payload["data"]

    def _paginate_repository_connection(
        self, *, query: str, connection: str, variables: Dict
    ) -> Iterator[Dict]:
        cursor = None

        while True:
            variables["cursor"] = cursor

            data = self._query(query, variables)
            conn_data = data["repository"][connection]

            yield from conn_data["nodes"]

            page = conn_data["pageInfo"]

            if not page["hasNextPage"]:
                break

            cursor = page["endCursor"]

    def fetch_pull_requests(
        self, prs_first: int = 50, comments_first: int = 50
    ) -> Iterator[Dict]:
        return self._paginate_repository_connection(
            query=build_pr_query(prs_first, comments_first),
            connection="pullRequests",
            variables={"owner": self.owner, "repo": self.repo_name},
        )

    def fetch_issues(
        self, prs_first: int = 50, comments_first: int = 50
    ) -> Iterator[Dict]:
        return self._paginate_repository_connection(
            query=build_issue_query(prs_first, comments_first),
            connection="issues",
            variables={"owner": self.owner, "repo": self.repo_name},
        )
