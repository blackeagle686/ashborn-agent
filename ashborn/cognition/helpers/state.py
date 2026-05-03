import json
import os
import threading

STATE_FILE = "execution_state.json"
_state_lock = threading.Lock()

def _load_state() -> dict:
    with _state_lock:
        if not os.path.exists(STATE_FILE):
            return {
                "execution_state": {
                    "completed_steps": [],
                    "pending_steps": [],
                    "failed_steps": []
                }
            }
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "execution_state": {
                    "completed_steps": [],
                    "pending_steps": [],
                    "failed_steps": []
                }
            }

def _save_state(data: dict) -> None:
    with _state_lock:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def _init_state_from_tasks(tasks: list) -> None:
    """Initialize state tracking from a newly generated list of tasks."""
    state_data = {
        "execution_state": {
            "completed_steps": [],
            "pending_steps": [],
            "failed_steps": []
        }
    }
    for t in tasks:
        state_data["execution_state"]["pending_steps"].append({
            "id": t.get("id"),
            "title": t.get("title", f"Task {t.get('id')}")
        })
    _save_state(state_data)

def _update_state(step_id: int, status: str, title: str = "") -> None:
    data = _load_state()
    state = data["execution_state"]
    
    # Remove step from all lists
    state["completed_steps"] = [s for s in state["completed_steps"] if s.get("id") != step_id]
    state["pending_steps"] = [s for s in state["pending_steps"] if s.get("id") != step_id]
    state["failed_steps"] = [s for s in state["failed_steps"] if s.get("id") != step_id]
    
    step_obj = {"id": step_id, "title": title}
    if status == "done":
        state["completed_steps"].append(step_obj)
    elif status == "failed":
        state["failed_steps"].append(step_obj)
    elif status == "pending":
        state["pending_steps"].append(step_obj)
        
    _save_state(data)

def _clear_state() -> None:
    with _state_lock:
        if os.path.exists(STATE_FILE):
            try: os.remove(STATE_FILE)
            except Exception: pass
