import json
import os
import threading
from .backbone import get_generations, add_generation, BACKBONE_FILE

GENERATION_FILE = BACKBONE_FILE

def _load_generation() -> dict:
    return {"generation_blocks": get_generations()}

def _save_generation(data: dict) -> None:
    # This is a bit tricky because _save_generation normally overwrites.
    # In the unified backbone, we might want to just append or replace the generations list.
    from .backbone import _load_backbone, _save_backbone
    backbone = _load_backbone()
    backbone["generations"] = data.get("generation_blocks", [])
    _save_backbone(backbone)

def _get_generation_blocks(plan_step_id: int) -> list:
    return [b for b in get_generations() if b.get("plan_step_id") == plan_step_id]

def _add_generation_block(block: dict) -> None:
    add_generation(block)
