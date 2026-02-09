

PULL_REQUEST_REFS = """
fragment PullRequestRefs on PullRequest {
    number
    baseRepository {
        ...RepositoryRefFields
    }
    headRepository{
        ...RepositoryRefFields
    }
    baseRefName
    headRefName
}
"""