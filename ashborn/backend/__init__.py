"""
Ashborn Backend Package.

Re-exports the FastAPI app and key shared state for backward compatibility.
"""
from .app import app
from .state import vscode_ipc_context, _pending_file_opens

__all__ = ["app", "vscode_ipc_context", "_pending_file_opens"]
