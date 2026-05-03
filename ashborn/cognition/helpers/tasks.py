import json
import os
import re
import threading
from .backbone import get_tasks, save_tasks, update_task_status, BACKBONE_FILE

# ── Task file path (kept for compatibility, though we now use BACKBONE_FILE) ────
TASK_FILE = BACKBONE_FILE 

def _load_tasks() -> dict:
    return {"tasks": get_tasks()}

def _save_tasks(data: dict) -> None:
    save_tasks(data.get("tasks", []), data.get("original_prompt"))

def _mark_task(task_id: int, status: str) -> None:
    update_task_status(task_id, status)

def _reset_failed_tasks() -> None:
    """Reset any failed tasks back to pending for resume."""
    tasks = get_tasks()
    modified = False
    for t in tasks:
        if t.get("status") == "failed":
            t["status"] = "pending"
            modified = True
    if modified:
        save_tasks(tasks)

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
    s = re.sub(r',\s*([\]}])', r'\1', s)
    
    return s
