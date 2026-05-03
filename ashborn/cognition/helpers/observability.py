import json
import uuid
import datetime
import os

TRACE_FILE = "ashborn.trace.jsonl"

def clear_logs() -> None:
    """Clear the trace log file for a new session/run."""
    if os.path.exists(TRACE_FILE):
        os.remove(TRACE_FILE)

def log_agent_action(agent: str, action: str, input_data: dict | str, output_data: dict | str | list, status: str) -> None:
    """
    Append an agent execution step to the JSONL trace log.
    Schema:
    {
      "log_id": "uuid",
      "agent": "generator",
      "action": "generate_code",
      "input": {},
      "output": {},
      "status": "success | failed",
      "timestamp": "ISO8601"
    }
    """
    log_entry = {
        "log_id": str(uuid.uuid4()),
        "agent": agent,
        "action": action,
        "input": input_data,
        "output": output_data,
        "status": status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        # dump with ensure_ascii=False to handle characters properly and compact separators to stay on one line
        f.write(json.dumps(log_entry, ensure_ascii=False, separators=(',', ':')) + "\n")
