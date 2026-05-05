"""
Ashborn Server — backward-compatibility shim.

All logic has moved to ashborn.backend.*
This file re-exports the symbols that other modules import from
`ashborn.server` so that existing code continues to work unchanged.
"""

# Re-export the FastAPI app (used by uvicorn: "ashborn.server:app")
from ashborn.backend.app import app  # noqa: F401

# Re-export shared state used by tools and cognition modules
from ashborn.backend.state import (        # noqa: F401
    vscode_ipc_context,
    _pending_file_opens,
)

# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ashborn.server:app", host="127.0.0.1", port=8765, reload=False)
