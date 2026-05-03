import json

# ── Task file path ─────────────────────────────────────────────────────────────
TASK_FILE = ".ashborn_tasks.json"

# ── Task file helpers ──────────────────────────────────────────────────────────

def _load_tasks() -> dict:
    with open(TASK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_tasks(data: dict) -> None:
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _mark_task(task_id: int, status: str) -> None:
    data = _load_tasks()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            break
    _save_tasks(data)

def _clean_json(raw: str) -> str:
    """Strip markdown fences and return bare JSON."""
    s = raw.strip()
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0].strip()
    elif "```" in s:
        s = s.split("```")[1].split("```")[0].strip()
    return s
