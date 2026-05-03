import json
import os
import threading
from .backbone import get_execution_state, update_execution_state, init_execution_state, _clear_backbone, BACKBONE_FILE

STATE_FILE = BACKBONE_FILE

def _load_state() -> dict:
    return {"execution_state": get_execution_state()}

def _save_state(data: dict) -> None:
    # Normally we update individual steps, but if needed we could replace the whole state
    from .backbone import _load_backbone, _save_backbone
    backbone = _load_backbone()
    backbone["execution_state"] = data.get("execution_state", {})
    _save_backbone(backbone)

def _init_state_from_tasks(tasks: list) -> None:
    init_execution_state(tasks)

def _update_state(step_id: int, status: str, title: str = "") -> None:
    update_execution_state(step_id, status, title)

def _clear_state() -> None:
    _clear_backbone()
