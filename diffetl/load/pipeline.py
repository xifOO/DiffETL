from typing import Optional
from diffetl.extract.client import GitHubClient
from diffetl.extract.repository import LocalGitRepository
from diffetl.transform.commit import CommitElement, CommitGraph
from diffetl.transform.diff import Diff, DiffElement
from diffetl.transform.groups import CommitGroup


def print_history(commit_element: CommitElement, graph: CommitGraph, depth=0):
    indent = "  " * depth
    print(f"{indent}↳ {commit_element.commit.hexsha[:6]} {commit_element.commit.message[:50]}...")
    for parent in graph.iter_parents(commit_element):
        print_history(parent, graph, depth + 1)

def print_diff(diff: Optional[Diff], depth=0):
    if diff is None:
        print("No diff available")
        return

    indent = "  " * depth
    stats = diff.get_aggregated_stats()
    
    print(f"{indent}Diff for commit: {diff.commit_hexsha}")
    print(f"{indent}Stats:")
    print(f"{indent} Files changed : {stats.files_changed}")
    print(f"{indent} Lines added   : {stats.lines_added}")
    print(f"{indent} Lines removed : {stats.lines_removed}")
    print(f"{indent} Hunks count   : {stats.hunks_count}")
    
    for element in diff.get_root_elements():
        print_diff_element(element, depth + 1)

def print_diff_element(element: DiffElement, depth=0):
    indent = "  " * depth
    print(f"{indent}- {element.element_type.name} | id: {element.identifier} | change: {element.change_type.name} | {element.stats.files_changed}")
    for child in element.children:
        print_diff_element(child, depth + 1)


client = GitHubClient("https://github.com/xifOO/gitk")
repo = LocalGitRepository(client)
commits = repo.fetch_commits(25, "master")

graph = CommitGraph(list(commits.values()))

group = CommitGroup().add_all(commits)
b = group.by_author(commits)

first_commit = next(iter(commits.values())) 
print_history(first_commit, graph)

for commit in commits.values():
    print_diff(commit.diff)
    print("-" * 40)
    