import json
import os
import threading

PLAN_FILE = "ashborn.plan.json"
_plan_lock = threading.Lock()

def _load_plan() -> dict:
    with _plan_lock:
        if not os.path.exists(PLAN_FILE):
            return {"plan_steps": []}
        try:
            with open(PLAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"plan_steps": []}

def _save_plan(data: dict) -> None:
    with _plan_lock:
        with open(PLAN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def _mark_plan_step(step_id: int, status: str) -> None:
    data = _load_plan()
    for s in data.get("plan_steps", []):
        if s.get("plan_step_id") == step_id:
            s["status"] = status
            break
    _save_plan(data)

def _get_executable_plan_steps(task_id: int) -> list:
    data = _load_plan()
    all_steps = data.get("plan_steps", [])
    step_status_map = {s.get("plan_step_id"): s.get("status") for s in all_steps}
    
    executable = []
    for s in all_steps:
        if s.get("task_id") != task_id or s.get("status") != "pending":
            continue
            
        deps = s.get("dependencies", [])
        deps_met = True
        deps_failed = False
        for d in deps:
            st = step_status_map.get(d, "done")
            if st == "failed":
                deps_failed = True
            elif st != "done":
                deps_met = False
                
        if deps_failed:
            _mark_plan_step(s.get("plan_step_id"), "failed")
            continue
            
        if deps_met:
            executable.append(s)
            
    return sorted(executable, key=lambda s: s.get("step_index", 99))

def _get_pending_plan_steps(task_id: int) -> list:
    """Returns ALL pending steps regardless of dependencies, useful for checking if a task is fully finished."""
    data = _load_plan()
    return [s for s in data.get("plan_steps", []) if s.get("task_id") == task_id and s.get("status") == "pending"]
