from diffetl.extract.graphql.fragments.actor import ACTOR_FIELDS
from diffetl.extract.graphql.fragments.comments import COMMENTS_FIELDS
from diffetl.extract.graphql.fragments.git_refs import PULL_REQUEST_REFS
from diffetl.extract.graphql.fragments.pr import PULL_REQUEST_CORE
from diffetl.extract.graphql.fragments.repository import REPOSITORY_REF_FIELDS


def build_pr_query(prs_first: int = 50, comments_first: int = 20) -> str:
    return "\n".join(
        [
            ACTOR_FIELDS,
            REPOSITORY_REF_FIELDS,
            COMMENTS_FIELDS,
            PULL_REQUEST_CORE,
            PULL_REQUEST_REFS,
            f"""
            query($owner: String!, $repo: String!, $cursor: String) {{
                repository(owner: $owner, name: $repo) {{
                    pullRequests(first: {prs_first}, after: $cursor) {{
                        pageInfo {{
                            hasNextPage
                            endCursor
                        }}
                        nodes {{
                            __typename
                            ...PullRequestRefs
                            ...PullRequestCore

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
