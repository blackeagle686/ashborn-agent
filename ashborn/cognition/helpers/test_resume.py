import asyncio
import os
import json
from ashborn.cognition.helpers.tasks import _save_tasks, TASK_FILE
from ashborn.cognition.helpers.plan import _save_plan, PLAN_FILE
from ashborn.cognition.helpers.state import STATE_FILE, _load_state
from ashborn.agent import get_ashborn_agent

async def test_resume():
    print("--- Testing Resume Logic ---")
    
    # 1. Manually create a failed task state
    tasks = {
        "tasks": [
            {
                "id": 1,
                "priority": 1,
                "type": "command",
                "title": "Failed Task",
                "description": "This task failed previously",
                "dependencies": [],
                "status": "failed"
            }
        ]
    }
    _save_tasks(tasks)
    
    plan = {
        "plan_steps": [
            {
                "plan_step_id": 101,
                "task_id": 1,
                "step_index": 1,
                "type": "command",
                "status": "failed",
                "dependencies": [],
                "solution": {"approach": "echo 'fail'"}
            }
        ]
    }
    _save_plan(plan)
    
    # Also create state file
    state = {
        "execution_state": {
            "completed_steps": [],
            "pending_steps": [],
            "failed_steps": [{"id": 1, "title": "Failed Task"}]
        }
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

    agent = await get_ashborn_agent()
    
    print("Attempting to resume...")
    # We use prompt="resume" to trigger the logic
    async for chunk in agent.run_stream("resume"):
        if chunk.get("type") == "status":
            print(f"STATUS: {chunk.get('content')}")
        elif chunk.get("type") == "chunk":
            print(chunk.get("content"), end="")

    # Verify task status is now 'done' or similar if it succeeded (mocking success by just running it)
    with open(TASK_FILE, "r") as f:
        final_tasks = json.load(f)
        print(f"\nFinal Task Status: {final_tasks['tasks'][0]['status']}")

    if not os.path.exists(TASK_FILE):
        print("Success: Files cleaned up after successful resume.")
    else:
        print("Note: Files still exist (maybe more tasks were pending or it failed again).")

if __name__ == "__main__":
    # Ensure we are in a clean state or at least known state
    for f in [TASK_FILE, PLAN_FILE, STATE_FILE]:
        if os.path.exists(f): os.remove(f)
    
    asyncio.run(test_resume())
