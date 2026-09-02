from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
import logging
import os
from typing import Mapping

from clickhouse_connect import get_client as raw_get_client
from diffetl.settings import store


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
def _get_cached_client(user: ClickHouseUser, host: str, port: int):
    creds = get_clickhouse_creds(user)
    
    return raw_get_client(
        host=host,
        port=port,
        user=creds.user,
        password=creds.password,
        connect_timeout=store.CLICKHOUSE_CONNECT_TIMEOUT, 
        send_receive_timeout=store.CLICKHOUSE_SEND_RECEIVE_TIMEOUT, 
    )


def default_client(user: ClickHouseUser = ClickHouseUser.DEFAULT, host: str = store.CLICKHOUSE_HOST, port: int = store.CLICKHOUSE_PORT):
    return _get_cached_client(user, host, port)