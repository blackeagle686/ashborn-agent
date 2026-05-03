import os
import sys

# Add parent dir to sys path
sys.path.append(os.getcwd())

from ashborn.cognition.helpers.schemas import validate_schema, TASK_SCHEMA, PLAN_SCHEMA, GENERATION_SCHEMA
from ashborn.cognition.loop import AshbornLoop
from ashborn.cognition.generator import AshbornGenerator

def test_schemas():
    print("--- Testing Schema Validation ---")
    
    # 1. Valid Task
    valid_task = {
        "original_prompt": "test",
        "tasks": [{"id": 1, "priority": 1, "type": "new_file", "title": "t", "status": "pending", "description": "d"}]
    }
    errors = validate_schema(valid_task, TASK_SCHEMA)
    print(f"Valid Task Errors: {errors} (Expected: [])")
    
    # 2. Invalid Task (missing type)
    invalid_task = {
        "original_prompt": "test",
        "tasks": [{"id": 1, "priority": 1, "title": "t", "status": "pending"}]
    }
    errors = validate_schema(invalid_task, TASK_SCHEMA)
    print(f"Invalid Task Errors: {errors} (Expected: ['Item 0 in 'tasks' missing required key: 'type''])")

def test_safety_validation():
    print("\n--- Testing Safety Validation ---")
    
    # Create a mock loop (we only need the validation method)
    # We'll use a dummy class to avoid __init__ issues
    class MockLoop(AshbornLoop):
        def __init__(self): pass
    
    loop = MockLoop()
    
    # 1. Safe Actions
    safe_actions = [{"tool": "file_write", "kwargs": {"path": "test.txt", "content": "hi"}}]
    errors = loop._pre_execution_validate(safe_actions)
    print(f"Safe Action Errors: {errors} (Expected: [])")
    
    # 2. Unsafe Path (Absolute)
    unsafe_path = [{"tool": "file_write", "kwargs": {"path": "/etc/passwd", "content": "hi"}}]
    errors = loop._pre_execution_validate(unsafe_path)
    print(f"Unsafe Path Errors: {errors} (Expected: contains Safety Violation)")
    
    # 3. Unsafe Command
    unsafe_cmd = [{"tool": "terminal", "kwargs": {"command": "rm -rf /"}}]
    errors = loop._pre_execution_validate(unsafe_cmd)
    print(f"Unsafe Command Errors: {errors} (Expected: contains Safety Violation)")

def test_generator_artifact_validation():
    print("\n--- Testing Generator Artifact Validation ---")
    gen = AshbornGenerator(None)
    
    # 1. Safe path
    err = gen._validate_artifact({"type": "file_write", "path": "src/main.py", "code": "print(1)"})
    print(f"Safe Artifact Error: {err} (Expected: None)")
    
    # 2. Directory traversal
    err = gen._validate_artifact({"type": "file_write", "path": "../outside.py", "code": "print(1)"})
    print(f"Traversal Artifact Error: {err} (Expected: contains Security Error)")

if __name__ == "__main__":
    test_schemas()
    test_safety_validation()
    test_generator_artifact_validation()
