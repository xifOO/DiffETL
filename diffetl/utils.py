from git import Diff as GitDiff


def is_binary_file(diff_item: GitDiff) -> bool:
    try:
        if hasattr(diff_item, 'diff') and diff_item.diff:
            diff_data = diff_item.diff[:1024]
            if isinstance(diff_data, bytes): 
                return b'\x00' in diff_data
        return False
    except Exception:
        return False