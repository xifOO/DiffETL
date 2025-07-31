from diffetl.extract.repository import GitHubClient
from diffetl.transform.commit import CommitElement
from diffetl.transform.groups import CommitGroup


def print_history(commit_element: CommitElement, depth=0):
    indent = "  " * depth
    print(f"{indent}↳ {commit_element.commit.hexsha[:6]} {commit_element.commit.message[:50]}...")
    for parent in commit_element.iter_parents():
        print_history(parent, depth + 1)


client = GitHubClient("https://github.com/xifOO/gitk")
commits = client.list_commits(10)

commits_elements = CommitElement.from_commits_list(commits)

group = CommitGroup().by_author(commits_elements)

first_commit = next(iter(commits_elements.values())) 
print_history(first_commit)