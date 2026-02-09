ISSUE_CORE = """
fragment IssueCore on Issue {
    number
    title
    bodyText
    state
    createdAt
    closedAt
    author {
        ...ActorFields
    }
}
"""