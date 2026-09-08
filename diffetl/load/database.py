from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Mapping, TypeAlias

from clickhouse_connect import get_client as raw_get_client
from clickhouse_connect.driver import Client
from diffetl.settings import store


ClickHouseClient: TypeAlias = Client


class ClickHouseUser(StrEnum):
    DEFAULT = "default"
    INGEST = "git_ingest"
    MIGRATIONS = "migrations"
    ANALYTICS = "analytics"


@dataclass
class ClickHouseCredentials:
    user: str
    password: str = field(repr=False)


__user_dict: Mapping[ClickHouseUser, ClickHouseCredentials] | None = None

def init_clickhouse_users() -> Mapping[ClickHouseUser, ClickHouseCredentials]:
    user_dict = {
        ClickHouseUser.DEFAULT: ClickHouseCredentials(
            user=store.CLICKHOUSE_USER,
            password=store.CLICKHOUSE_PASSWORD
        )
    }
    for u in ClickHouseUser:
        user = os.getenv(f"CLICKHOUSE_{u.name.upper()}_USER")
        password = os.getenv(f"CLICKHOUSE_{u.name.upper()}_PASSWORD")
        if user and password:
            user_dict[u] = ClickHouseCredentials(user=user, password=password)

    user_names = ",".join([x.name for x in user_dict.keys()])
    logging.warning(f"initialized clickhouse users: {user_names}")
    return user_dict


def get_clickhouse_creds(user: ClickHouseUser) -> ClickHouseCredentials:
    global __user_dict
    if not __user_dict:
        __user_dict = init_clickhouse_users()
    return __user_dict.get(user, __user_dict[ClickHouseUser.DEFAULT])


@lru_cache(maxsize=len(ClickHouseUser))
def _get_cached_client(user: ClickHouseUser, host: str, port: int, database: str) -> ClickHouseClient:
    creds = get_clickhouse_creds(user)
    
    return raw_get_client(
        host=host,
        port=port,
        user=creds.user,
        password=creds.password,
        database=database,
        connect_timeout=store.CLICKHOUSE_CONNECT_TIMEOUT, 
        send_receive_timeout=store.CLICKHOUSE_SEND_RECEIVE_TIMEOUT, 
    )


def default_client(
    user: ClickHouseUser = ClickHouseUser.DEFAULT, 
    host: str = store.CLICKHOUSE_HOST, 
    port: int = store.CLICKHOUSE_PORT,
    database: str = store.CLICKHOUSE_DATABASE
) -> ClickHouseClient:
    return _get_cached_client(user, host, port, database)


def make_migrations(client: ClickHouseClient, database_name: str = "analytics", migrations_dir: Path = Path(__file__).parent / "migrations") -> None:
    client.command(f"CREATE DATABASE IF NOT EXISTS {database_name}")
    client.command("""
        CREATE TABLE IF NOT EXISTS schema_migrations
        (version String, applied_at DateTime DEFAULT now())
        ENGINE = MergeTree ORDER BY version
    """)

    applied = {row[0] for row in client.query("SELECT version FROM schema_migrations").result_rows}

    for sql_file in sorted(migrations_dir.glob("*.sql")):
        version = sql_file.stem
        if version in applied:
            continue
        ddl = sql_file.read_text()
        for statement in ddl.split(";"):
            if statement.strip():
                client.command(statement)
        client.command(
            "INSERT INTO schema_migrations (version) VALUES (%(v)s)",
            parameters={"v": version},
        )
