# Phoenix AI Framework - Update Notes

The following changes were made to the core Phoenix library inside the `.venv` to support better progress feedback and logging control.

## Changes

### 1. Configuration (`phoenix.core.config`)
- **Added `LOG_LEVEL`**: Introduced a `LOG_LEVEL` configuration variable that defaults to `"INFO"` but can be overridden via environment variables.

### 2. LLM Streaming (`phoenix.llm.openai`)
- **`generate_stream`**: Implemented token-by-token streaming using OpenAI's `stream=True`. It now yields content chunks as they arrive from the API and saves the full interaction to memory once complete.

### 3. Logging (`phoenix.observability.logger`)
- **Dynamic Log Level**: Updated `get_logger` to respect `config.LOG_LEVEL`. This allows users to suppress telemetry logs by setting `LOG_LEVEL=WARNING`.

### 3. Startup Progress (`phoenix.main`)
- **Startup Callback**: Added `on_progress` support to `startup_phoenix`. It now reports progress percentages (0.1 to 1.0) and descriptive messages for each initialization step (Cache, LLM, Vector DB, VLM, Audio).

### 5. Agent Loop (`phoenix.agent.loop`)
- **Progress Callback**: Added `on_progress` support to `AgentLoop.run`.
- **`run_stream`**: New async generator method that yields `status` and `chunk` events.
- **Dynamic Summary**: Added a final synthesis step that generates a streaming Markdown summary of the agent's actions once a plan is complete.

### 6. Agent Interface (`phoenix.agent.agent`)
- **`run_stream`**: Propagates streaming functionality from both `fast_ans` and `plan` modes to the caller.
- **Classification Progress**: Added a progress update for the request classification step in `"auto"` mode.

## Rationale
These changes were necessary to provide a more responsive and professional CLI experience. By silencing verbose telemetry logs and showing dynamic progress messages, the agent feels more alive and less cluttered.
