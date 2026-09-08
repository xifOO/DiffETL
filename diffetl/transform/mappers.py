from typing import Any, Dict, List

from diffetl.transform.issue import IssueElement
from diffetl.transform.pr import PullRequestElement

ColumnBatch = Dict[str, List[Any]]

def pull_requests_to_columns(prs: List[PullRequestElement]) -> ColumnBatch:
    return {
        'number': [pr.ref.number for pr in prs],
        'source_repo': [pr.ref.source_repo for pr in prs],
        'target_repo': [pr.ref.target_repo for pr in prs],
        'is_fork': [int(pr.ref.is_fork) for pr in prs],
        'title': [pr.title for pr in prs],
        'description': [pr.description for pr in prs],
        'state': [pr.state.value for pr in prs],
        'created_at': [pr.created_at for pr in prs],
        'merged_at': [pr.merged_at for pr in prs],
        'closed_at': [pr.closed_at for pr in prs],
        'author_name': [pr.author.name for pr in prs],
        'author_email': [pr.author.email for pr in prs],
        'target_branch': [pr.target_branch for pr in prs],
        'source_branch': [pr.source_branch for pr in prs],
    }


def pull_request_reviews_to_columns(prs: List[PullRequestElement]) -> ColumnBatch:
    cols: ColumnBatch = {
        "review_id": [],
        "author_name": [],
        "author_email": [],
        "body": [],
        "created_at": [],
        "state": [],
    }
    for pr in prs:
        for review in pr.reviews:
            cols['review_id'].append(review.review_id)
            cols['author_name'].append(review.author.name)
            cols['author_email'].append(review.author.email)
            cols['body'].append(review.body)
            cols['created_at'].append(review.created_at)
            cols['state'].append(review.state.value)
    return cols


def issue_to_columns(issues: List[IssueElement]) -> ColumnBatch:
    return {
        'number': [issue.number for issue in issues],
        'title': [issue.title for issue in issues],
        'description': [issue.description for issue in issues],
        'state': [issue.state.value for issue in issues],
        'created_at': [issue.created_at for issue in issues],
        'closed_at': [issue.closed_at for issue in issues],
        'author_name': [issue.author.name for issue in issues],
        'author_email': [issue.author.email for issue in issues],
    }