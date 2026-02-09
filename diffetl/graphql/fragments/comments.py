

COMMENTS_FIELDS = """
fragment PRCommentFields on IssueComment {
    bodyText
    createdAt
    author {
        ...ActorFields
    }
}
"""