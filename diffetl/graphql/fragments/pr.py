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
    baseRefName
    headRefName
}
"""