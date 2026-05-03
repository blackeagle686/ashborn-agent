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
    """Strip markdown fences and return bare JSON, handling some common malformations."""
    s = raw.strip()
    
    # 1. Strip markdown code fences
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0].strip()
    elif "```" in s:
        parts = s.split("```")
        if len(parts) >= 3:
            s = parts[1].strip()
        else:
            s = parts[0].strip()
            
    # 2. Heuristic: Find first { and last }
    start = s.find('{')
    end = s.rfind('}')
    if start != -1 and end != -1:
        s = s[start:end+1]
        
    # 3. Handle common malformations like trailing commas
    # This is a bit risky but often helpful: remove comma before ] or }
    s = re.sub(r',\s*([\]}])', r'\1', s)
    
    return s
