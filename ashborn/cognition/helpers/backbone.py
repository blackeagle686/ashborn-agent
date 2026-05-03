import json
import os
import threading
import uuid
from datetime import datetime

BACKBONE_FILE = "ashborn.context.json"
_backbone_lock = threading.Lock()

def _load_backbone() -> dict:
    with _backbone_lock:
        if not os.path.exists(BACKBONE_FILE):
            return {
                "context_id": str(uuid.uuid4()),
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "original_prompt": ""
                },
                "tasks": [],
                "plans": [],
                "generations": [],
                "execution_state": {
                    "completed_steps": [],
                    "pending_steps": [],
                    "failed_steps": []
                },
                "memory": {}
            }
        try:
            with open(BACKBONE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "context_id": str(uuid.uuid4()),
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                "tasks": [],
                "plans": [],
                "generations": [],
                "execution_state": {
                    "completed_steps": [],
                    "pending_steps": [],
                    "failed_steps": []
                },
                "memory": {}
            }

def _save_backbone(data: dict) -> None:
    data["metadata"]["updated_at"] = datetime.now().isoformat()
    with _backbone_lock:
        with open(BACKBONE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def _clear_backbone() -> None:
    with _backbone_lock:
        if os.path.exists(BACKBONE_FILE):
            try: os.remove(BACKBONE_FILE)
            except Exception: pass

# --- Task Helpers ---
def get_tasks() -> list:
    return _load_backbone().get("tasks", [])

def save_tasks(tasks: list, original_prompt: str = None) -> None:
    data = _load_backbone()
    data["tasks"] = tasks
    if original_prompt:
        data["metadata"]["original_prompt"] = original_prompt
    _save_backbone(data)

def update_task_status(task_id: int, status: str) -> None:
    data = _load_backbone()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            break
    _save_backbone(data)

# --- Plan Helpers ---
def get_plan_steps() -> list:
    return _load_backbone().get("plans", [])

def save_plan_steps(steps: list) -> None:
    data = _load_backbone()
    data["plans"] = steps
    _save_backbone(data)

def update_plan_step_status(step_id: int, status: str) -> None:
    data = _load_backbone()
    for s in data["plans"]:
        if s.get("plan_step_id") == step_id:
            s["status"] = status
            break
    _save_backbone(data)

# --- Generation Helpers ---
def get_generations() -> list:
    return _load_backbone().get("generations", [])

def add_generation(block: dict) -> None:
    data = _load_backbone()
    data.setdefault("generations", []).append(block)
    _save_backbone(data)

# --- State Helpers ---
def get_execution_state() -> dict:
    return _load_backbone().get("execution_state", {})

def update_execution_state(step_id: int, status: str, title: str = "") -> None:
    data = _load_backbone()
    state = data["execution_state"]
    
    # Remove from all
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
        
    _save_backbone(data)

def init_execution_state(tasks: list) -> None:
    data = _load_backbone()
    state = {
        "completed_steps": [],
        "pending_steps": [],
        "failed_steps": []
    }
    for t in tasks:
        state["pending_steps"].append({
            "id": t.get("id"),
            "title": t.get("title", f"Task {t.get('id')}")
        })
    data["execution_state"] = state
    _save_backbone(data)

# --- Memory Helpers ---
def set_memory_value(key: str, value: any) -> None:
    data = _load_backbone()
    data.setdefault("memory", {})[key] = value
    _save_backbone(data)

def get_memory_value(key: str, default: any = None) -> any:
    return _load_backbone().get("memory", {}).get(key, default)
