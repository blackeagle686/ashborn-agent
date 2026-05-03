import json
import os

PLAN_FILE = "ashborn.plan.json"

def _load_plan() -> dict:
    if not os.path.exists(PLAN_FILE):
        return {"plan_steps": []}
    try:
        with open(PLAN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"plan_steps": []}

def _save_plan(data: dict) -> None:
    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _mark_plan_step(step_id: int, status: str) -> None:
    data = _load_plan()
    for s in data.get("plan_steps", []):
        if s.get("plan_step_id") == step_id:
            s["status"] = status
            break
    _save_plan(data)

def _get_pending_plan_steps(task_id: int) -> list:
    data = _load_plan()
    return sorted(
        [s for s in data.get("plan_steps", []) if s.get("task_id") == task_id and s.get("status") == "pending"],
        key=lambda s: s.get("step_index", 99)
    )
