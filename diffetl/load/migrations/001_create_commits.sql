CREATE TABLE IF NOT EXISTS commits 
(
    hexsha String,
    message String,
    author_name Nullable(String),
    author_email Nullable(String),
    created_at DateTime,
    parents_hexsha Array(String),
    is_bot UInt8,
    bot_type Nullable(String),
    branch_types Array(String),
    has_lost_branch UInt8
)
ENGINE = MergeTree
ORDER BY (created_at, hexsha);