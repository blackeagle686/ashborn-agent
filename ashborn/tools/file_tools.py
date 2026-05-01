"""
Ashborn Precision File Tools
─────────────────────────────
Provides two tools purpose-built to solve the "agent nukes file" problem:

1. file_read_lines  — Reads a file and prefixes every line with its number.
                      The LLM can reference exact line numbers in its edits.

2. file_update_multi — Applies a list of non-overlapping edits to a file.
                       Each edit can be:
                         • line_range  → replace lines L_start..L_end with new_content
                         • search      → exact-string search/replace (NO upsert fallback)
                       Edits are applied in REVERSE order so line numbers stay valid.
"""

import os
import re
from phoenix.framework.agent import tool


# ── Tool 1: Read with line numbers ────────────────────────────────────────────

@tool(
    name="file_read_lines",
    description=(
        "Reads a file and returns its content with LINE NUMBERS prefixed (e.g. 'L1: import os'). "
        "Use this BEFORE editing an existing file so you know the exact lines to target. "
        "Input: 'file_path' (str). Optional: 'start_line' (int), 'end_line' (int) to read a range."
    )
)
def file_read_lines_tool(file_path: str, start_line: int = None, end_line: int = None) -> str:
    """
    Returns file content with line numbers prefixed as 'L<n>: <text>'.
    Supports optional start/end range for large files.
    """
    if not os.path.exists(file_path):
        return f"ERROR: File not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)
        s = (start_line - 1) if start_line and start_line > 0 else 0
        e = end_line if end_line and end_line <= total else total

        numbered = []
        for i, line in enumerate(lines[s:e], start=s + 1):
            numbered.append(f"L{i}: {line.rstrip()}")

        header = f"[{file_path}] — {total} lines total"
        if start_line or end_line:
            header += f" (showing L{s+1}–L{e})"
        return header + "\n" + "\n".join(numbered)
    except Exception as ex:
        return f"ERROR reading {file_path}: {ex}"


# ── Tool 2: Multi-block precision editor ──────────────────────────────────────

@tool(
    name="file_update_multi",
    description=(
        "Applies multiple SURGICAL edits to an existing file. "
        "ALWAYS use this instead of file_write when the file already exists. "
        "Input: 'file_path' (str), 'edits' (list of edit objects). "
        "Each edit object must be ONE of these two forms:\n"
        "  • Line-range replace: {\"line_start\": N, \"line_end\": M, \"new_content\": \"...\"}  "
        "    → replaces lines N through M (inclusive, 1-indexed) with new_content.\n"
        "  • Exact search/replace: {\"search\": \"exact text\", \"replace\": \"new text\"}  "
        "    → finds the FIRST occurrence of 'search' and replaces it. Fails if not found.\n"
        "RULES:\n"
        "  1. Use file_read_lines first to see exact content and line numbers.\n"
        "  2. Keep edits minimal — only change what is necessary.\n"
        "  3. Do NOT rewrite the whole file; only specify the changed blocks.\n"
        "  4. Line-range edits are applied in reverse order automatically."
    )
)
def file_update_multi_tool(file_path: str, edits: list) -> str:
    """
    Applies a list of surgical edits to file_path.
    Supports 'line_range' (line_start, line_end, new_content) and
    'search_replace' (search, replace) edit types.
    """
    if not os.path.exists(file_path):
        return f"ERROR: File not found: {file_path}. Use file_write to create new files."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()  # preserve original line endings
    except Exception as ex:
        return f"ERROR reading {file_path}: {ex}"

    # ── Separate and validate edits ──────────────────────────────────────────
    line_edits = []   # (line_start, line_end, new_content)
    str_edits = []    # (search, replace)
    errors = []

    for i, edit in enumerate(edits):
        if "line_start" in edit and "line_end" in edit:
            ls = edit.get("line_start")
            le = edit.get("line_end")
            nc = edit.get("new_content", "")
            if not isinstance(ls, int) or not isinstance(le, int):
                errors.append(f"Edit #{i+1}: line_start/line_end must be integers.")
                continue
            if ls < 1 or le > len(lines) or ls > le:
                errors.append(
                    f"Edit #{i+1}: line range L{ls}–L{le} is out of bounds "
                    f"(file has {len(lines)} lines)."
                )
                continue
            line_edits.append((ls, le, nc))
        elif "search" in edit:
            s = edit.get("search", "")
            r = edit.get("replace", "")
            if not s:
                errors.append(f"Edit #{i+1}: 'search' cannot be empty.")
                continue
            str_edits.append((s, r))
        else:
            errors.append(
                f"Edit #{i+1}: unknown format — must have ('line_start','line_end','new_content') "
                "or ('search','replace')."
            )

    if errors:
        return "ERRORS in edit spec:\n" + "\n".join(errors)

    # ── Check for overlapping line edits ──────────────────────────────────────
    sorted_line_edits = sorted(line_edits, key=lambda x: x[0])
    for j in range(len(sorted_line_edits) - 1):
        if sorted_line_edits[j][1] >= sorted_line_edits[j + 1][0]:
            return (
                f"ERROR: Overlapping line edits: "
                f"L{sorted_line_edits[j][0]}–L{sorted_line_edits[j][1]} overlaps "
                f"L{sorted_line_edits[j+1][0]}–L{sorted_line_edits[j+1][1]}. "
                "Fix the edit ranges and try again."
            )

    # ── Apply line-range edits in REVERSE order ───────────────────────────────
    for ls, le, nc in sorted(line_edits, key=lambda x: x[0], reverse=True):
        # Split new_content into lines, preserving trailing newline behaviour
        if nc and not nc.endswith("\n"):
            nc += "\n"
        new_lines = nc.splitlines(keepends=True) if nc else []
        lines[ls - 1: le] = new_lines

    applied_line = len(line_edits)

    # ── Apply search/replace edits on the joined text ─────────────────────────
    content = "".join(lines)
    applied_str = 0
    str_errors = []

    for search, replace in str_edits:
        if search in content:
            content = content.replace(search, replace, 1)
            applied_str += 1
        else:
            str_errors.append(f"Search text not found: {repr(search[:80])}")

    if str_errors:
        return (
            f"Partial failure — applied {applied_line} line edits, "
            f"{applied_str}/{len(str_edits)} search-replace edits.\n"
            "Not-found searches:\n" + "\n".join(str_errors)
        )

    # ── Write result ──────────────────────────────────────────────────────────
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as ex:
        return f"ERROR writing {file_path}: {ex}"

    total_applied = applied_line + applied_str
    return (
        f"Successfully updated {file_path} — "
        f"{applied_line} line-range edit(s), {applied_str} search-replace edit(s) applied."
    )


# ── Tool 3: Reliable File Creator ─────────────────────────────────────────────

@tool(
    name="file_write",
    description=(
        "Creates a NEW file with the specified content. "
        "Use this ONLY for files that do not exist yet. "
        "Input: 'file_path' (str), 'content' (str). "
        "Automatically creates parent directories if they are missing."
    )
)
def file_write_tool(file_path: str, content: str) -> str:
    """
    Creates or overwrites a file. Ensures parent directories exist.
    """
    try:
        # Create parent directories if needed
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created file: {file_path}"
    except Exception as ex:
        return f"ERROR creating file {file_path}: {ex}"
