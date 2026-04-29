# Phoenix AI Framework - Optimization & Stability Notes (V1.1)

This document tracks the core library modifications made to the `phoenix` package to enhance performance, reliability, and the overall Ashborn Agent experience.

### 1. High-Performance Startup (`phoenix.main`)
- **Parallel Initialization**: Re-engineered `startup_phoenix` to use `asyncio.gather`. All core services (Cache, LLM, Vector DB, VLM, Audio) now initialize concurrently, drastically reducing boot time.
- **Lazy-Fast Startup**: Transitioned to a lazy-loading strategy for heavy models. The core engine now boots in parallel and finishes instantly, deferring heavy model loading (like Embeddings) until the first actual request is made.

### 2. LLM Performance & Control (`phoenix.llm`)
- **`max_tokens` Support**: Updated `BaseLLM` and `OpenAILLM` to support a granular `max_tokens` parameter.
- **Cognitive Optimization**: 
    - **Classification**: Now capped at 10 tokens for near-instant "PLAN vs FAST" decisions.
    - **Analysis**: Workspace scanning is capped at 150 tokens to force concise architectural summaries.
    - **Thinking**: Objective deconstruction is capped at 200 tokens to prevent "rambling" and reduce latency.

### 3. Iterative Code Generation (`phoenix.tools.io`)
- **`FileAppendTool`**: Introduced a new core tool (`file_append`) that allows for additive file updates.
- **Chunking Strategy**: Updated the `Planner` logic to favor multi-step "chunked" file creation. This prevents hallucinations and truncation errors during complex coding tasks by building files logically (Imports -> Structure -> Implementation).

### 4. Anti-Hallucination Measures (`phoenix.agent`)
- **Validation in Loop**: The `AgentLoop` now tracks if any actual tool actions were performed. If the agent tries to finish without taking action, the final summary prompt is dynamically adjusted to demand accountability.
- **Planner Strictness**: Added "Actions Over Talking" and "Verify Completion" rules to the Planner's system prompt to prevent the agent from falsely claiming success.

### 5. UI/UX & Silencing (`phoenix.observability`, `phoenix.vector`)
- **Telemetry Suppression**: Standardized `LOG_LEVEL` usage across the framework.
- **Chroma & Embeddings**: Replaced all internal `print` statements with `logger.info`, ensuring the Ashborn CLI remains clean and professional when `LOG_LEVEL=WARNING` is set.

### 6. Streaming Architecture (`phoenix.agent.loop`)
- **Event-Driven Flow**: Implemented `run_stream` which yields `status` (for cognition) and `chunk` (for final answer) events, allowing for the premium two-phase UI transition in the CLI.

### 7. Surgical File Patching (V1.2)
- **`FileEditTool`**: Introduced a search-and-replace patching tool (`file_edit`) that supports multi-block updates and "Upsert" logic (appending if search string is not found).
- **Precision Planning**: Re-engineered the `Planner`'s cognitive strategy to favor `file_read` -> `file_edit` loops. This significantly reduces token overhead and prevents file truncation during complex updates.
- **Auto-Creation**: The new tool automatically handles directory and file creation if they don't exist, streamlining the project generation workflow.

### 8. Semantic Response Caching (V1.3)
- **Vector-Based Cache**: Implemented a `SemanticCache` that stores `(prompt, response)` pairs as embeddings.
- **Fast Similarity Hits**: The `InsightEngine` now checks for semantically similar prompts before calling the LLM. If a match exceeds the `0.95` similarity threshold, the cached answer is returned instantly.
- **Latency Reduction**: This update drastically improves response times for repeated or slightly varied user queries while maintaining high accuracy.
