from enum import Enum
import mimetypes
from typing import Optional

import magic


class DiffType(Enum):
    COMMIT = "commit"
    FILE = "file"
    HUNK = "hunk"
    LINE_GROUP = "line_group"


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    COPIED = "copied"
    TYPE_CHANGED = "type_changed"
    UNCHANGED = "unchanged"

    @classmethod
    def from_git_flag(cls, flag: str) -> Optional['ChangeType']:
        mapping = {
            'A': cls.ADDED,
            'D': cls.REMOVED,
            'M': cls.MODIFIED,
            'R': cls.RENAMED,
            'C': cls.COPIED,
            'T': cls.TYPE_CHANGED,
            'U': cls.UNCHANGED
        }
        return mapping.get(flag.upper(), None)
        

class FileType(Enum):
    SOURCE_CODE = "source_code"
    TEST = "test"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    BUILD = "build"
    DATA = "data"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"

    @classmethod
    def from_path_to_content(cls, file_path: str, content: Optional[bytes] = None) -> 'FileType':
        mime_type: Optional[str] = None

        if content is not None:
            try:
                mime_type = magic.from_buffer(content, mime=True)
            except Exception:
                pass
        
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_path)
        
        path_lower = file_path.lower()

        if "/test/" in path_lower or "/tests/" in path_lower or path_lower.startswith("tests") or path_lower.endswith(("_test.py", ".spec.ts", "-test.js")):
            return cls.TEST
        elif "/docs/" in path_lower or "/doc/" in path_lower or path_lower.startswith("docs/") or path_lower.startswith("documentation/") or path_lower.endswith((".md", ".rst")):
            return cls.DOCUMENTATION
        elif "/build/" in path_lower or path_lower.startswith("build/") or "makefile" in path_lower or ".sh" in path_lower or ".bat" in path_lower:
            return cls.BUILD
        elif "/data/" in path_lower or path_lower.startswith("data/"):
            if mime_type and (mime_type.startswith("text/x-") or mime_type.startswith("application/x-")):
                pass 
            else:
                return cls.DATA
        
        if mime_type:
            if mime_type.startswith("text/"):
                if mime_type in ['text/x-python', 'text/javascript', 'text/x-java-source', 'text/x-c', 'text/x-c++', 'text/x-go', 'text/x-php', 'text/x-ruby', 'text/html']:
                    return cls.SOURCE_CODE
                if 'json' in mime_type or 'xml' in mime_type or 'yaml' in mime_type or 'ini' in mime_type:
                    return cls.CONFIG
                return cls.DATA

            elif mime_type.startswith("application/"):
                if any(ext in mime_type for ext in ['json', 'xml', 'yaml', 'ini']):
                    return cls.CONFIG
                if any(ext in mime_type for ext in ['zip', 'tar', 'gzip', 'rar', 'x-bzip2']):
                    return cls.ARCHIVE
                if mime_type in ['application/x-sh', 'application/x-executable', 'application/octet-stream']:
                    return cls.BUILD
                return cls.SOURCE_CODE
            
            elif mime_type.startswith('image/'):
                return cls.IMAGE
            elif mime_type.startswith('audio/'):
                return cls.AUDIO
            elif mime_type.startswith('video/'):
                return cls.VIDEO
        return cls.UNKNOWN
