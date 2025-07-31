from pathlib import Path


BASE_SAVE_DIR = Path.home() / "Documents/save_repos/"


def get_repo_dir(repo_url: str) -> Path:
    repo_name = repo_url.strip().rstrip("/").split("/")[-1].replace(".git", "")
    return Path(BASE_SAVE_DIR / repo_name)