PULL_REQUEST_CORE = """
fragment PullRequestCore on PullRequest {
    title
    bodyText
    state
    isDraft
    createdAt
    mergedAt
    closedAt
    author {
        ...ActorFields
    }
}
"""


PULL_REQUEST_REVIEW_FIELDS = """
fragment PullRequestReviewFields on PullRequestReview {
    bodyText
    createdAt
    state
    author {
        ...ActorFields
    }
}
"""
