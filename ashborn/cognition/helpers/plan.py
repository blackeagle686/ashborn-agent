import json
import os
import threading
from .backbone import get_plan_steps, save_plan_steps, update_plan_step_status, BACKBONE_FILE

PLAN_FILE = BACKBONE_FILE

def _load_plan() -> dict:
    return {"plan_steps": get_plan_steps()}

def _save_plan(data: dict) -> None:
    save_plan_steps(data.get("plan_steps", []))

def _mark_plan_step(step_id: int, status: str) -> None:
    update_plan_step_status(step_id, status)

def _reset_failed_plan_steps() -> None:
    """Reset any failed plan steps back to pending for resume."""
    steps = get_plan_steps()
    modified = False
    for s in steps:
        if s.get("status") == "failed":
            s["status"] = "pending"
            modified = True
    if modified:
        save_plan_steps(steps)

def _get_executable_plan_steps(task_id: int) -> list:
    all_steps = get_plan_steps()
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
            update_plan_step_status(s.get("plan_step_id"), "failed")
            continue
            
        if deps_met:
            executable.append(s)
            
    return sorted(executable, key=lambda s: s.get("step_index", 99))

def _get_pending_plan_steps(task_id: int) -> list:
    """Returns ALL pending steps regardless of dependencies, useful for checking if a task is fully finished."""
    return [s for s in get_plan_steps() if s.get("task_id") == task_id and s.get("status") == "pending"]
