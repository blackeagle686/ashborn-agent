"""
Ashborn Backend — shared server state and context variables.
"""
import logging
from contextvars import ContextVar
from collections import deque
from typing import Optional

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s"
)
log = logging.getLogger("ashborn.server")

# ── IPC Context ───────────────────────────────────────────────────────────────
# Allows tools to access the VS Code IPC bridge for the current request
vscode_ipc_context: ContextVar[Optional[callable]] = ContextVar("vscode_ipc", default=None)

# Thread-safe queue for file-open requests emitted by sync tools
_pending_file_opens: deque = deque()

# ── Global agent & IPC response futures ───────────────────────────────────────
_agent = None

# Stores Futures for tool calls waiting for VS Code response: { call_id: Future }
_ipc_responses: dict = {}


def get_agent():
    return _agent


def set_agent(agent):
    global _agent
    _agent = agent
