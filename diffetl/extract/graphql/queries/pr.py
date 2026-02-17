from diffetl.extract.graphql.fragments.actor import ACTOR_FIELDS
from diffetl.extract.graphql.fragments.comments import COMMENTS_FIELDS
from diffetl.extract.graphql.fragments.git_refs import PULL_REQUEST_REFS
from diffetl.extract.graphql.fragments.pr import (
    PULL_REQUEST_CORE,
    PULL_REQUEST_REVIEW_FIELDS,
)
from diffetl.extract.graphql.fragments.repository import REPOSITORY_REF_FIELDS


def build_pr_query(prs_first: int, reviews_first: int, comments_first: int) -> str:
    return "\n".join(
        [
            ACTOR_FIELDS,
            REPOSITORY_REF_FIELDS,
            COMMENTS_FIELDS,
            PULL_REQUEST_CORE,
            PULL_REQUEST_REFS,
            PULL_REQUEST_REVIEW_FIELDS,
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
                            
                            reviews(first: {reviews_first}) {{
                                nodes {{
                                    ...PullRequestReviewFields
                                }}
                            }}

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
