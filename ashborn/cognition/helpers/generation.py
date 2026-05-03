import json
import os

GENERATION_FILE = "ashborn.generation.json"

def _load_generation() -> dict:
    if not os.path.exists(GENERATION_FILE):
        return {"generation_blocks": []}
    try:
        with open(GENERATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"generation_blocks": []}

def _save_generation(data: dict) -> None:
    with open(GENERATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _get_generation_blocks(plan_step_id: int) -> list:
    data = _load_generation()
    return [b for b in data.get("generation_blocks", []) if b.get("plan_step_id") == plan_step_id]

def _add_generation_block(block: dict) -> None:
    data = _load_generation()
    data.setdefault("generation_blocks", []).append(block)
    _save_generation(data)
