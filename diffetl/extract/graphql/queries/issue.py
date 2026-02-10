from diffetl.extract.graphql.fragments.actor import ACTOR_FIELDS
from diffetl.extract.graphql.fragments.comments import COMMENTS_FIELDS
from diffetl.extract.graphql.fragments.issue import ISSUE_CORE


def build_issue_query(issues_first: int = 50, comments_first: int = 20):
    return "\n".join(
        [
            ACTOR_FIELDS,
            COMMENTS_FIELDS,
            ISSUE_CORE,
            f"""
            query($owner: String!, $repo: String!, $cursor: String) {{
                repository(owner: $owner, name: $repo) {{
                    issues(first: {issues_first}, after: $cursor) {{
                        pageInfo {{
                            hasNextPage
                            endCursor
                        }}
                        nodes {{
                            __typename
                            ...IssueCore
                            
                            comments(first: {comments_first}) {{
                                nodes {{
                                    ...PRCommentFields
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """,
        ]
    )
