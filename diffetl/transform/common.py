from datetime import datetime
from typing import Optional


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def parse_dt_opt(value: Optional[str]) -> Optional[datetime]:
    return parse_dt(value) if value is not None else None