# Phoenix AI Framework - Update Notes

The following changes were made to the core Phoenix library inside the `.venv` to support better progress feedback and logging control.

## Changes

### 1. Configuration (`phoenix.core.config`)
- **Added `LOG_LEVEL`**: Introduced a `LOG_LEVEL` configuration variable that defaults to `"INFO"` but can be overridden via environment variables.

### 2. Logging (`phoenix.observability.logger`)
- **Dynamic Log Level**: Updated `get_logger` to respect `config.LOG_LEVEL`. This allows users to suppress telemetry logs by setting `LOG_LEVEL=WARNING`.

### 3. Startup Progress (`phoenix.main`)
- **Startup Callback**: Added `on_progress` support to `startup_phoenix`. It now reports progress percentages (0.1 to 1.0) and descriptive messages for each initialization step (Cache, LLM, Vector DB, VLM, Audio).

### 4. Agent Loop (`phoenix.agent.loop`)
- **Progress Callback**: Added `on_progress` support to `AgentLoop.run`.
- **Descriptive Updates**: The loop now emits progress messages during:
    - Initial awareness (workspace analysis and objective thinking).
    - Each planning step.
    - Action execution.
    - Reflection phase.

### 4. Agent Interface (`phoenix.agent.agent`)
- **Propagated Progress Callback**: Updated `Agent.run` to accept the `on_progress` callback and pass it down to the `AgentLoop`.
- **Classification Progress**: Added a progress update for the request classification step in `"auto"` mode.

## Rationale
These changes were necessary to provide a more responsive and professional CLI experience. By silencing verbose telemetry logs and showing dynamic progress messages, the agent feels more alive and less cluttered.
