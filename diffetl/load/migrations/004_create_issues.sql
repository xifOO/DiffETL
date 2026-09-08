CREATE TABLE IF NOT EXISTS issues
(
    number Int32,
    title String,
    description Nullable(String),
    state Enum8('OPEN'=1, 'CLOSED'=2),
    created_at DateTime,
    closed_at Nullable(DateTime), 
    author_name String,
    author_email Nullable(String)
)
ENGINE = MergeTree
ORDER BY (number, created_at);
