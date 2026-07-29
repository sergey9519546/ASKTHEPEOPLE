"""Path-traversal defense for user-supplied ids used in filesystem paths."""
import os
from werkzeug.utils import secure_filename


class SafePathError(ValueError):
    """Raised when a user-supplied path component escapes its base directory."""


def safe_join(base_dir: str, user_id: str) -> str:
    """
    Join a user-supplied id onto base_dir, rejecting anything that escapes base_dir.

    Defense layers:
      1. Reject empty/None immediately.
      2. secure_filename() — strips '..', separators, null bytes, empties.
         If it MANGLES the input (output != stripped input), the id contained
         traversal/illegal characters -> reject. Legit ids (uuids, hex) survive unchanged.
      3. Canonicalize BOTH paths with os.path.realpath() and verify the target
         stays within base via os.path.commonpath() — robust against absolute
         paths, symlinks, and any remaining traversal tricks.
    """
    if not user_id:
        raise SafePathError("Empty path parameter")
    cleaned = secure_filename(user_id)
    if not cleaned or cleaned != user_id.strip():
        raise SafePathError("Invalid characters in path parameter")
    base_real = os.path.realpath(base_dir)
    target_real = os.path.realpath(os.path.join(base_real, cleaned))
    try:
        if os.path.commonpath([base_real, target_real]) != base_real:
            raise SafePathError("Path traversal attempt detected")
    except ValueError:
        # commonpath raises if paths are on different drives (Windows) — deny.
        raise SafePathError("Path traversal attempt detected")
    return target_real
