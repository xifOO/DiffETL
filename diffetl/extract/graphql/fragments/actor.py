ACTOR_FIELDS = """
fragment ActorFields on Actor {
    login
    ... on User {
        email
    }
}
"""
