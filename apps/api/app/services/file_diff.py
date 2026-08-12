"""Git-style unified diff helpers for agent file-change reporting."""

from difflib import unified_diff
from typing import Tuple

# Cap persisted diffs so a huge generated file can't bloat the event store.
_MAX_DIFF_LINES = 400


def compute_unified_diff(
    old_content: str,
    new_content: str,
    path: str,
) -> Tuple[str, int, int]:
    """Return ``(diff_text, added_lines, removed_lines)`` for a file change.

    ``diff_text`` is a unified diff (``a/path`` → ``b/path``) suitable for a
    git-style viewer. ``added``/``removed`` count changed lines (excluding the
    ``---``/``+++`` file headers).
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    diff_lines = list(
        unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )
    added = sum(
        1
        for line in diff_lines
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1
        for line in diff_lines
        if line.startswith("-") and not line.startswith("---")
    )
    total = len(diff_lines)
    if total > _MAX_DIFF_LINES:
        diff_lines = diff_lines[:_MAX_DIFF_LINES]
        diff_lines.append(
            f"... diff truncated ({total - _MAX_DIFF_LINES} more lines)"
        )
    return "\n".join(diff_lines), added, removed
