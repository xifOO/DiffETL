import urllib.parse
from abc import abstractmethod
from typing import Dict, Iterator, List, Optional, Tuple

from git import Commit as GitCommit
from git import Repo
from requests_cache import CachedSession, FileCache

from diffetl.config import BASE_GITHUB_API, get_repo_dir
from diffetl.extract._client import GitClient


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
    def fetch_pull_requests(self, state: str) -> Iterator[Dict]: ...

    @abstractmethod
    def fetch_issues(self, state: str) -> Iterator[Dict]: ...


class GithubAPIClient(APIClient):
    def __init__(self, repo_url: str, token: Optional[str] = None) -> None:
        super().__init__(repo_url, token)
        self.base_url = BASE_GITHUB_API.format(self.owner, self.repo_name)
        self.session = CachedSession(
            "diffetl",
            backend=FileCache(
                cache_name="github_api_cache",
                use_cache_dir=True,
                serializer="json",
            ),
            expire_after=1024,
            allowable_methods=["GET"],
            allowable_codes=[200, 304],
        )
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _fetch(self, url: str, state: str, sort: str, direction: str) -> Iterator[Dict]:
        params = {
            "state": state,
            "per_page": 100,
            "page": 1,
            "sort": sort,
            "direction": direction,
        }

        while True:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()

            data = resp.json()

            if not data:
                break

            yield from data

            params["page"] += 1

    def fetch_pull_requests(
        self, state: str = "all", sort="created", direction="asc"
    ) -> Iterator[Dict]:
        url = self.base_url + "/pulls"
        return self._fetch(url, state, sort, direction)

    def fetch_issues(
        self, state: str = "all", sort="created", direction="asc"
    ) -> Iterator[Dict]:
        url = self.base_url + "/issues"
        yield from (
            item
            for item in self._fetch(url, state, sort, direction)
            if "pull_request" not in item
        )
