CREATE TABLE IF NOT EXISTS pull_request_reviews
(
    review_id String,
    author_name String,
    author_email Nullable(String),
    body String,
    created_at DateTime,
    state Enum8('approved'=1, 'changes_requested'=2, 'commented'=3, 'dismissed'=4, 'pending'=5), 
    version DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (review_id, created_at);