CREATE TABLE IF NOT EXISTS pull_requests
(
    number UInt32,
    source_repo String,
    target_repo String,
    is_fork UInt8,
    title String,
    description Nullable(String),
    state Enum8('open'=1, 'closed'=2, 'merged'=3, 'draft'=4), 
    created_at DateTime,
    merged_at Nullable(DateTime),
    closed_at Nullable(DateTime),
    author_name String,
    author_email Nullable(String),
    target_branch String,
    source_branch String,
)
ENGINE = MergeTree
ORDER BY (created_at, number);