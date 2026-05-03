import os
import json
from ashborn.cognition.helpers.backbone import BACKBONE_FILE, _load_backbone
from ashborn.cognition.helpers.tasks import _save_tasks, _load_tasks
from ashborn.cognition.helpers.plan import _save_plan, _load_plan
from ashborn.cognition.helpers.state import _update_state, _load_state

def test_backbone():
    print("--- Testing Shared Context Backbone ---")
    
    # 1. Clear any existing backbone
    if os.path.exists(BACKBONE_FILE):
        os.remove(BACKBONE_FILE)
    
    # 2. Save tasks using tasks helper
    tasks = {"tasks": [{"id": 1, "title": "Test Task", "status": "pending"}]}
    _save_tasks(tasks)
    print("Tasks saved.")
    
    # 3. Save plan using plan helper
    plan = {"plan_steps": [{"plan_step_id": 101, "task_id": 1, "status": "pending"}]}
    _save_plan(plan)
    print("Plan saved.")
    
    # 4. Update state using state helper
    _update_state(1, "pending", "Test Task")
    print("State updated.")
    
    # 5. Load backbone directly and verify everything is in ONE file
    if os.path.exists(BACKBONE_FILE):
        print(f"Success: Backbone file '{BACKBONE_FILE}' exists.")
        with open(BACKBONE_FILE, "r") as f:
            data = json.load(f)
            
            has_tasks = len(data.get("tasks", [])) > 0
            has_plans = len(data.get("plans", [])) > 0
            has_state = len(data.get("execution_state", {}).get("pending_steps", [])) > 0
            
            if has_tasks and has_plans and has_state:
                print("Success: Tasks, Plans, and State are all present in the same file.")
                print(f"Context ID: {data.get('context_id')}")
            else:
                print("Failure: Missing data in backbone.")
                print(f"Tasks: {has_tasks}, Plans: {has_plans}, State: {has_state}")
    else:
        print("Failure: Backbone file not found.")

if __name__ == "__main__":
    test_backbone()
    # Cleanup after test
    if os.path.exists(BACKBONE_FILE):
        os.remove(BACKBONE_FILE)
