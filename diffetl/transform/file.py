from dataclasses import dataclass
from typing import Optional

from diffetl.transform._enum import FileType


@dataclass
class FileMetadata:
    mode: Optional[str] = None
    is_binary: bool = False
    type: FileType = FileType.UNKNOWN
    