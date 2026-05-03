import json

# --- Schema Definitions ---

TASK_SCHEMA = {
    "type": "object",
    "required": ["original_prompt", "tasks"],
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "required": ["id", "priority", "type", "title", "status"],
                "properties": {
                    "type": {"enum": ["new_file", "modify_file", "command", "read"]}
                }
            }
        }
    }
}

PLAN_SCHEMA = {
    "type": "object",
    "required": ["plan_steps"],
    "properties": {
        "plan_steps": {
            "type": "array",
            "items": {
                "required": ["plan_step_id", "task_id", "type", "status", "solution"],
                "properties": {
                    "type": {"enum": ["analysis", "design", "implementation", "validation"]}
                }
            }
        }
    }
}

GENERATION_SCHEMA = {
    "type": "object",
    "required": ["generation_blocks"],
    "properties": {
        "generation_blocks": {
            "type": "array",
            "items": {
                "required": ["generate_block_id", "plan_step_id", "artifacts", "status"],
                "properties": {
                    "artifacts": {
                        "type": "array",
                        "items": {
                            "required": ["type", "path", "code"],
                            "properties": {
                                "type": {"enum": ["file_write", "file_update_multi", "terminal"]}
                            }
                        }
                    }
                }
            }
        }
    }
}

def validate_schema(data: dict, schema: dict) -> list:
    """Very basic schema validator. Returns a list of error strings."""
    errors = []
    
    # Check required top-level keys
    for key in schema.get("required", []):
        if key not in data:
            errors.append(f"Missing required key: '{key}'")
            
    # Check arrays
    for key, prop in schema.get("properties", {}).items():
        if key in data:
            val = data[key]
            if prop.get("type") == "array":
                if not isinstance(val, list):
                    errors.append(f"Key '{key}' must be an array")
                    continue
                
                # Check items in array
                item_schema = prop.get("items", {})
                required_items = item_schema.get("required", [])
                for i, item in enumerate(val):
                    if not isinstance(item, dict):
                        errors.append(f"Item {i} in '{key}' must be an object")
                        continue
                    for k in required_items:
                        if k not in item:
                            errors.append(f"Item {i} in '{key}' missing required key: '{k}'")
                    
                    # Check enums
                    item_props = item_schema.get("properties", {})
                    for k, v in item_props.items():
                        if k in item and "enum" in v:
                            if item[k] not in v["enum"]:
                                errors.append(f"Item {i} in '{key}' key '{k}' has invalid value '{item[k]}'. Expected one of {v['enum']}")
                                
    return errors
