"""
Ashborn Loop Utilities — extracted helpers for the main agent loop.
Handles task querying, artifact mapping, safety validation, and approval.
"""
import json
import os
import asyncio

from .helpers.tasks import TASK_FILE, _load_tasks, _mark_task
from .helpers.plan import PLAN_FILE
from .helpers.generation import GENERATION_FILE
from .helpers.state import STATE_FILE


# ---------------------------------------------------------------------------
# Task queries
# ---------------------------------------------------------------------------

def get_pending_tasks() -> list:
    """Return pending tasks sorted by priority."""
    try:
        data = _load_tasks()
        return sorted(
            [t for t in data.get("tasks", []) if t.get("status") == "pending"],
            key=lambda t: t.get("priority", 99),
        )
    except Exception:
        return []


def get_executable_tasks() -> list:
    """Return pending tasks whose dependencies are all met."""
    try:
        data = _load_tasks()
        all_tasks = data.get("tasks", [])
        status_map = {t.get("id"): t.get("status") for t in all_tasks}

        executable = []
        for t in all_tasks:
            if t.get("status") != "pending":
                continue
            deps_met, deps_failed = True, False
            for d in t.get("dependencies", []):
                s = status_map.get(d, "done")
                if s == "failed":
                    deps_failed = True
                elif s != "done":
                    deps_met = False

            if deps_failed:
                _mark_task(t.get("id"), "failed")
                continue
            if deps_met:
                executable.append(t)

        return sorted(executable, key=lambda t: t.get("priority", 99))
    except Exception:
        return []


def has_task_file() -> bool:
    return os.path.exists(TASK_FILE)


# ---------------------------------------------------------------------------
# Artifact → Action mapping
# ---------------------------------------------------------------------------

def _detect_vscode() -> bool:
    try:
        from ashborn.server import vscode_ipc_context
        return vscode_ipc_context.get() is not None
    except ImportError:
        return False


def map_artifacts_to_actions(generation_blocks: list) -> list:
    """Convert generation-block artifacts into executable action dicts."""
    is_vscode = _detect_vscode()
    actions = []
    for block in generation_blocks:
        for art in block.get("artifacts", []):
            art_type = art.get("type")

            if art_type == "file_write":
                tool = "vscode_create_file" if is_vscode else "file_write"
                key = "path" if is_vscode else "file_path"
                actions.append({"tool": tool, "kwargs": {key: art.get("path", ""), "content": art.get("code", "")}})

            elif art_type == "file_update_multi":
                chunks = art.get("edits")
                if not chunks and "code" in art:
                    try:
                        chunks = json.loads(art["code"]) if isinstance(art["code"], str) else art["code"]
                    except Exception:
                        chunks = []
                if not chunks:
                    continue
                actions.append({
                    "tool": "file_update_multi",
                    "kwargs": {"file_path": art.get("path", ""), "edits": chunks},
                })

            elif art_type == "terminal":
                tool = "vscode_terminal_run" if is_vscode else "terminal"
                actions.append({"tool": tool, "kwargs": {"command": art.get("code", "")}})

    return actions


# ---------------------------------------------------------------------------
# Safety & Approval
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS = ["rm -rf /", "mkfs", "dd if="]
SENSITIVE_TOOLS = ["terminal", "vscode_terminal_run"]
SAFE_COMMANDS = ["ls", "pwd", "mkdir -p", "touch", "cat", "git status"]


def pre_execution_validate(actions: list) -> list:
    """Return a list of safety-violation strings (empty = all clear)."""
    errors = []
    for act in actions:
        tool = act.get("tool")
        kwargs = act.get("kwargs", {})

        path = kwargs.get("path") or kwargs.get("file_path")
        if path and (path.startswith("/") or ".." in path):
            errors.append(f"Safety Violation: Path '{path}' is absolute or contains '..'")

        if tool in SENSITIVE_TOOLS:
            cmd = kwargs.get("command", "")
            for pat in FORBIDDEN_PATTERNS:
                if pat in cmd:
                    errors.append(f"Safety Violation: Command '{cmd}' contains forbidden pattern '{pat}'")
    return errors


def is_sensitive_action(actions: list) -> bool:
    """True if any action needs explicit user approval."""
    for act in actions:
        if act.get("tool") in SENSITIVE_TOOLS:
            cmd = act.get("kwargs", {}).get("command", "").strip()
            if not any(cmd.startswith(s) for s in SAFE_COMMANDS):
                return True
    return False


async def check_and_ask_approval(actions: list) -> tuple[bool, list]:
    """Request VS Code IPC approval for sensitive actions."""
    if not is_sensitive_action(actions):
        return True, actions

    from ashborn.server import vscode_ipc_context
    ipc_call = vscode_ipc_context.get()
    if not ipc_call:
        return True, actions

    try:
        raw_res = await ipc_call("ask_approval", {"actions": actions})
        res = json.loads(raw_res)
        if res.get("decision") == "approved":
            return True, res.get("modified_actions", actions)
        return False, actions
    except Exception as e:
        print(f"[LOOP ERROR] Approval request failed: {e}")
        return False, actions


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

ALL_STATE_FILES = [TASK_FILE, PLAN_FILE, GENERATION_FILE, STATE_FILE]


def cleanup_state_files():
    """Remove all state files (task, plan, generation, state)."""
    for f in ALL_STATE_FILES:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def is_all_done() -> bool:
    """True when every task in the task file has status 'done'."""
    try:
        data = _load_tasks()
        return all(t.get("status") == "done" for t in data.get("tasks", []))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Background task scheduling
# ---------------------------------------------------------------------------

def schedule_background(background_tasks: set, coro):
    """Fire-and-forget a coroutine, tracking it in *background_tasks*."""
    task = asyncio.create_task(coro)
    background_tasks.add(task)

    def _on_done(t):
        background_tasks.discard(t)
        try:
            _ = t.exception()
        except Exception:
            pass

    task.add_done_callback(_on_done)
