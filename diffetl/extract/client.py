from abc import abstractmethod
import logging
import random
import textwrap
import time
import urllib.parse
from typing import Any, Dict, Iterator, List, NoReturn, Optional, Tuple, TypedDict, Union

import requests
from git import Commit as GitCommit
from git import Repo

from diffetl.config import get_repo_dir
from diffetl.extract.graphql.queries.issue import build_issue_query
from diffetl.extract.graphql.queries.pr import build_pr_query
from diffetl.exceptions import APIConnectionError
from diffetl.settings.store import GITHUB_TOKEN, default_graphql_url, is_dev


def _create_cacheable_session():
    import requests_cache 
    from diffetl.settings.store import _is_cacheable, http_cache_ttl_seconds
    
    return requests_cache.CachedSession(
        ".cache/github_graphql",
        backend="sqlite",
        allowable_methods=("POST",), 
        expire_after=http_cache_ttl_seconds(), 
        filter_fn=_is_cacheable,       
    )

class GitClient:
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
        force_last_sha = not skip

        for gc in iterator_gc:
            if skip:
                if gc.hexsha == last_sha:
                    skip = False
                    force_last_sha = True
                continue
            batch.append(gc)
            if len(batch) == batch_size:
                break

        if last_sha is not None and not force_last_sha:
            # force-push/rebase - lash_sha not exists
            raise ValueError(
                f"last_sha {last_sha} not found in branch {branch} history"
            )

        new_last_sha = batch[-1].hexsha if batch else last_sha
        return batch, new_last_sha


class HTTPClient:

    class _Proxy(TypedDict):
        http: Optional[str]
        https: Optional[str]

    MAX_DELAY = 5
    INITIAL_DELAY = 0.5
    _proxy: Optional[_Proxy]
    _verify_ssl_certs: bool
    
    def __init__(
        self,
        repo_url: str,
        token: Optional[str] = None,
        timeout: Union[float, Tuple[float, float]] = 80,
        session: Optional[requests.Session] = None,
        verify_ssl_certs: bool = True,
        proxy: Optional[Union[str, _Proxy]] = None,
    ) -> None:
        self.owner, self.repo_name = self._parse_repo_url(repo_url)
        self._token = token or GITHUB_TOKEN
        if not self._token:
            raise ValueError(
                "GitHub token not provided: pass token= explicitly "
                "or set the GITHUB_TOKEN environment variable."
            )
        self._verify_ssl_certs = verify_ssl_certs
        self._session = session
        self._timeout = timeout

        if proxy:
            if isinstance(proxy, str):
                proxy = HTTPClient._Proxy(http=proxy, https=proxy)
            if not isinstance(proxy, dict):
                raise ValueError(
                    "Proxy(ies) must be specified as either a string "
                    "URL or a dict() with string URL under the "
                    "'https' and/or 'http' keys."
                )

        self._proxy = proxy.copy() if proxy else None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} owner={self.owner!r} repo={self.repo_name!r}"

    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
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

    def _should_retry(
        self,
        response: Optional[requests.Response],
        exc: Optional[Exception],
        num_retries: int,
        max_network_retries: int,
    ) -> bool:
        if num_retries >= max_network_retries:
            return False

        if exc is not None:
            return getattr(exc, "should_retry", False)

        if response is None:
            return False

        if response.status_code >= 500:
            return True

        if response.status_code in (200, 403, 429):
            try:
                errors = response.json().get("errors", [])
            except ValueError:
                return False
            return any(e.get("type") == "RATE_LIMITED" for e in errors)

        return False
        
    def _sleep_time_seconds(self, num_retries: int) -> float:
        sleep_seconds = min(
            HTTPClient.INITIAL_DELAY * (2 ** (num_retries - 1)),
            HTTPClient.MAX_DELAY,
        )

        sleep_seconds = self._add_jitter_time(sleep_seconds)
        sleep_seconds = max(HTTPClient.INITIAL_DELAY, sleep_seconds)

        return sleep_seconds

    def _add_jitter_time(self, sleep_seconds: float) -> float:
        sleep_seconds *= 0.5 * (1 + random.uniform(0, 1))
        return sleep_seconds

    def request(
        self,
        method: str,
        url: str,
        max_network_retries: int,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        num_retries = 0

        while True:
            try:
                response = self._request_internal(method, url, json_body)
                connection_error = None
            except APIConnectionError as e:
                connection_error = e
                response = None

            if self._should_retry(
                response, connection_error, num_retries, max_network_retries
            ):
                if connection_error:
                    logging.info(
                        "Encountered a retryable error: %s",
                        connection_error.user_message
                    )

                num_retries += 1
                sleep_time = self._sleep_time_seconds(num_retries)
                logging.info(
                    "Initiating retry %d for request %s %s after "
                    "sleeping %.2f seconds.",
                    num_retries, method, url, sleep_time,
                )
                time.sleep(sleep_time)
            else:
                if response is not None:
                    return response
                
                assert connection_error is not None
                raise connection_error

    def _request_internal(
        self,
        method: str,
        url: str,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        kwargs: Dict[str, Any] = {
            "headers": {"Authorization": f"Bearer {self._token}"},
            "timeout": self._timeout,
            "verify": self._verify_ssl_certs,
        }

        if json_body is not None:
            kwargs["json"] = json_body

        if self._proxy:
            kwargs["proxies"] = self._proxy

        if self._session is None:
            if is_dev():
                self._session = _create_cacheable_session()
            else:
                self._session = requests.Session()

        try:
            return self._session.request(method, url, **kwargs)
        except Exception as e:
            self._handle_request_error(e)

    def _handle_request_error(self, e: Exception) -> NoReturn:
        if isinstance(e, requests.exceptions.SSLError):
            msg = (
                "Could not verify SSL certificate. Please make"
                "sure that your network is not intercepting certificates. "
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = False

        elif isinstance(
            e, 
            (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ),
        ):
            msg = (
                "Connection error."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = True

        elif isinstance(e, requests.exceptions.RequestException):
            msg = (
                "Unexpected error."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = False
        else:
            msg = (
                "Unexpected error. "
                "It looks like there's probably a configuration "
            )
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
            should_retry = False

        msg = textwrap.fill(msg) + "\n\n(Network error: %s)" % (err,)
        raise APIConnectionError(msg, should_retry=should_retry) from e

    def close(self):
        if self._session is not None:
            self._session.close()

    @abstractmethod
    def fetch_pull_requests(
        self,
        batch_size: int,
        reviews_first: int,
        comments_first: int,
        last_cursor: Optional[str] = None, 
    ) -> Iterator[Dict]: ...

    @abstractmethod
    def fetch_issues(
        self,
        batch_size: int,
        comments_first: int,
        last_cursor: Optional[str] = None, 
    ) -> Iterator[Dict]: ...

    
class GithubGraphQLClient(HTTPClient):
    def __init__(
        self, 
        repo_url: str, 
        token: Optional[str] = None,
        graphql_url: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(repo_url, token, **kwargs)
        self._graphql_url = graphql_url or default_graphql_url()

    def _query(self, query: str, variables=None):
        resp = self.request(
            "POST",
            self._graphql_url,
            max_network_retries=3,
            json_body={"query": query, "variables": variables or {}},
        )
        payload = resp.json()

        if "errors" in payload:
            raise RuntimeError(payload["errors"])

        return payload["data"]

    def _fetch_batch(
        self,
        query: str,
        connection: str,
        last_cursor: Optional[str] = None,
    ) -> Tuple[List[Dict], Optional[str], bool]:
        variables = {"owner": self.owner, "repo": self.repo_name}

        if last_cursor:
            variables["cursor"] = last_cursor 

        data = self._query(query, variables=variables)
        conn = data["repository"][connection]
        page = conn["pageInfo"]
        return conn["nodes"], page["endCursor"], page["hasNextPage"]

    def fetch_pull_requests(
        self,
        batch_size: int,
        reviews_first: int,
        comments_first: int,
        last_cursor: Optional[str] = None,
    ) -> Iterator[Dict]:
        query = build_pr_query(batch_size, reviews_first, comments_first)
        has_next_page = True

        while has_next_page:
            nodes, last_cursor, has_next_page = self._fetch_batch(
                query, "pullRequests", last_cursor=last_cursor
            )
            yield from nodes

    def fetch_issues(
        self,
        batch_size: int,
        comments_first: int,
        last_cursor: Optional[str] = None,
    ) -> Iterator[Dict]:
        query = build_issue_query(batch_size, comments_first)
        has_next_page = True

        while has_next_page:
            nodes, last_cursor, has_next_page = self._fetch_batch(
                query, "issues", last_cursor=last_cursor
            )
            yield from nodes