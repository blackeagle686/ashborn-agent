# 🐦🔥 Phoenix AI: Autonomous Agent Framework Guide

The Phoenix AI Agent Framework is a high-performance, modular system designed for building autonomous agents that can think, plan, and execute complex tasks. It moves beyond simple chat interfaces to create agents capable of engineering, research, and multi-step reasoning.

---

## 🐦🔥 Cognitive Architecture

The Phoenix Agent operates on a "Cognitive Loop" inspired by human problem-solving patterns. Each step of the loop is handled by a specialized module:

1.  **Analyzer**: Concurrently scans the project structure, tech stack, and environment to provide the agent with "situational awareness."
2.  **Thinker**: Deconstructs the user prompt into core objectives and constraints.
3.  **Planner**: Generates a sequence of steps and selects the necessary tools to achieve the objectives.
4.  **Actor**: Executes the planned actions, potentially in parallel, using the Tool Manager.
5.  **Reflector**: Evaluates the outcome of actions, verifies results, and provides insights for the next iteration.

---

## 🐦🔥 Getting Started

### 1. Basic Initialization

To use the agent, you need to initialize the Phoenix framework and then instantiate the `Agent` class.

```python
import asyncio
from phoenix import init_phoenix, startup_phoenix
from phoenix.agent import Agent

async def main():
    # 1. Initialize core services
    init_phoenix()
    await startup_phoenix()
    
    # 2. Create the agent (uses default OpenAI LLM and Hybrid Memory)
    agent = Agent()
    
    # 3. Run a task
    response = await agent.run("Create a summary of all files in the current directory.")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.1 Startup Performance Upgrades

Phoenix startup now initializes core services concurrently. Heavy local models (like embeddings) still load lazily on first real use, so boot is fast while preserving full capability.

```python
from phoenix import init_phoenix, startup_phoenix

init_phoenix(local=False, vlm=False)  # choose providers
await startup_phoenix()               # parallel async startup
```

### 2. Execution Modes

The agent supports three execution modes via the `mode` parameter in `agent.run()`:

*   **`auto`** (Default): The agent decides if it can answer immediately or if it needs to enter a planning loop.
*   **`plan`**: Forces the agent into the full `Think -> Plan -> Act -> Reflect` loop. Best for complex tasks.
*   **`fast_ans`**: Bypasses the loop and provides a direct answer using available memory context. Best for simple questions.

```python
# Force planning for complex engineering
await agent.run("Refactor the memory module to support Redis.", mode="plan")

# Quick greeting
await agent.run("Who are you?", mode="fast_ans")
```

### 3. Streaming Mode (`run_stream`)

Use `run_stream` to get event-based output:
- `status` events for cognition/execution progress
- `chunk` events for streamed text

This now includes planner thinking text in planning mode.

```python
async for event in agent.run_stream("Refactor planner for reliability", mode="plan"):
    if event["type"] == "status":
        print(f"[status] {event['content']}")
    elif event["type"] == "chunk":
        print(event["content"], end="")
```

---

## 🛠️ Tool Integration

The agent's power comes from its tools. You can easily register custom tools using the `@tool` decorator.

```python
from phoenix.tools import tool

@tool(name="fetch_weather", description="Fetches the current weather for a city. Input: 'city' (str).")
def weather_tool(city: str):
    # Your custom logic here
    return f"The weather in {city} is sunny, 25°C."

# Register the tool to the agent
agent.register_tool(weather_tool)
```

### Built-in Engineering File Tools (Upgraded)

- `file_read`: read file contents
- `file_write`: full overwrite
- `file_append`: additive writes (great for chunked generation)
- `file_edit`: search/replace patch tool with upsert behavior
- `file_update_multi`: multi-block in-place updates

The planner is optimized to prefer precision loops (`file_read -> file_edit`) for existing files and chunked appends for large new files.

---

## 🔧 Extensibility: Bring Your Own Components

You can replace any core cognition/execution module without forking Phoenix:
- `thinker`
- `planner`
- `analyzer`
- `actor`
- `reflector`
- `tool_manager`
- `loop` (instance) or `loop_cls` (class)

### A) Inject Custom Modules

```python
from phoenix.agent import Agent

agent = Agent(
    thinker=my_thinker,
    planner=my_planner,
    analyzer=my_analyzer,
    actor=my_actor,
    reflector=my_reflector,
)
```

### B) Use a Custom Agent Loop

```python
class MyLoop:
    def __init__(self, thinker, planner, actor, reflector, analyzer):
        self.thinker = thinker
        self.planner = planner
        self.actor = actor
        self.reflector = reflector
        self.analyzer = analyzer

    async def run(self, prompt, memory, session_id, max_iterations=5):
        return "custom loop result"

    async def run_stream(self, prompt, memory, session_id, max_iterations=5):
        yield {"type": "status", "content": "custom thinking"}
        yield {"type": "chunk", "content": "custom output\n"}

agent = Agent(loop_cls=MyLoop)
```

### C) Runtime Replacement (Hot Swap)

```python
agent.set_component("planner", my_new_planner, rebuild_loop=True)
agent.rebuild_loop()  # optional explicit refresh
```

### D) Factory-Based Construction

```python
agent = Agent(
    component_factories={
        "thinker": lambda **ctx: MyThinker(ctx["llm"]),
        "planner": lambda **ctx: MyPlanner(ctx["llm"], ctx["tools"]),
    }
)
```

---

## 🧠 Planner Thinking Visibility

The planner now exposes streamed reasoning text during `run_stream` via `Planner.stream_thinking(...)`.  
This is designed for UI transparency (show users what the agent is planning before tool actions run).

---

## ⚙️ LLM Controls & Reliability Upgrades

- `max_tokens` is now supported in LLM generation calls.
- Auto-mode classification is constrained for low-latency routing (`PLAN` vs `FAST`).
- Cognitive modules use bounded output budgets to reduce rambling and latency.
- Agent loop includes an anti-false-finish guard: planner cannot complete before meaningful actions are executed.

---

## 🚀 Semantic Insight Caching

`InsightEngine` now supports semantic response caching using embeddings:
- checks similar prior prompts before calling LLM
- returns cached answer when similarity threshold is high
- improves latency for repeated/rephrased questions

---

## 🧠 Memory Customization (Latest)

Phoenix now supports interactive memory workflows and custom user memory backends.

### 1) Interactive Hybrid Memory APIs

`HybridMemory` now supports structured context operations in addition to plain chat turns:

- `add_context_item(session_id, key, value, source="user")`
- `get_context_bundle(session_id, query="")`

`get_context_bundle(...)` returns a structured dictionary for advanced UI/loop use:
- `session_variables`
- `reflections`
- `recent_conversation`
- `full_text`

```python
from phoenix.memory.hybrid import HybridMemory

memory = HybridMemory()
await memory.add_interaction("s1", "user", "hello", metadata={"project": "IRYM"})
await memory.add_context_item("s1", "repo", "phoenix-ai", source="system")
bundle = await memory.get_context_bundle("s1", query="hello")
print(bundle["session_variables"])
```

### 2) Plug Your Own Memory Backend

You can pass custom memory directly to `Agent(...)`.  
If your memory object does not fully match Phoenix internals, it will be wrapped by `InteractiveMemoryAdapter`.

Supported custom method signatures (any compatible subset):

- write: `add_interaction(...)` or `add_message(...)` or `store(...)`
- read: `get_full_context(...)` or `get_context(...)`

```python
class MyMemory:
    async def add_message(self, session_id, role, content, metadata=None):
        ...

    async def get_context(self, session_id, query=""):
        return "custom context"

agent = Agent(memory=MyMemory())
```

### 3) Reflection Runs in Background

To reduce latency, reflection consolidation and reflection log persistence are now scheduled as background operations inside `AgentLoop`.  
This means users get faster responses while reflection state is still persisted asynchronously.

---

## 🌐 Connecting to Applications

### 💻 CLI Integration (Interactive)

You can create a simple interactive CLI to chat with your agent.

```python
import asyncio
from phoenix import init_phoenix, startup_phoenix
from phoenix.agent import Agent

async def interactive_cli():
    init_phoenix()
    await startup_phoenix()
    agent = Agent()
    
    print("🐦🔥 Phoenix Agent CLI (type 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        # Run agent in auto mode
        response = await agent.run(user_input, mode="auto")
        print(f"\nPhoenix: {response}\n")

if __name__ == "__main__":
    asyncio.run(interactive_cli())
```

### ⚡ FastAPI Integration

FastAPI is ideal for asynchronous AI services. Use lifecycle hooks for clean initialization.

```python
from fastapi import FastAPI, Body
from phoenix import init_phoenix_full
from phoenix.agent import Agent
from contextlib import asynccontextmanager

# Global agent instance
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    await init_phoenix_full()
    agent = Agent()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/agent/chat")
async def chat_with_agent(
    prompt: str = Body(..., embed=True),
    session_id: str = Body(None, embed=True)
):
    response = await agent.run(prompt, session_id=session_id)
    return {"answer": response, "session_id": session_id}
```

### 🎸 Django Integration

For Django, you can use `asyncio.run()` or build an `AsyncJsonWebsocketConsumer` for real-time streaming (recommended).

#### Simple View Example:
> [!IMPORTANT]
> For production-grade Django setups using the **Singleton Pattern**, thread-safe initialization, and real-time WebSockets (Channels), see the full **[Django Integration Guide](./DJANGO_INTEGRATION.md)**.

```python
# views.py
from django.http import JsonResponse
from phoenix.agent import Agent
from phoenix import init_phoenix, startup_phoenix
import asyncio

# Singleton agent for simplicity (or use a service manager)
_agent = None

async def get_agent():
    global _agent
    if _agent is None:
        init_phoenix()
        await startup_phoenix()
        _agent = Agent()
    return _agent

def agent_view(request):
    prompt = request.GET.get('q')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    agent = loop.run_until_complete(get_agent())
    response = loop.run_until_complete(agent.run(prompt))
    
    return JsonResponse({"reply": response})
```

### 🎨 GUI Integration (Desktop & Web)

> [!TIP]
> For a more detailed guide on professional GUI patterns (PyQt6, Threading, and advanced Streamlit), check out the **[GUI Integration Guide](./GUI_INTEGRATION.md)**.

#### **A. Streamlit (Modern Web GUI)**
Streamlit is the fastest way to build a web interface for your agent.

```python
import streamlit as st
import asyncio
from phoenix import init_phoenix, startup_phoenix
from phoenix.agent import Agent

# Page config
st.set_page_config(page_title="Phoenix AI Agent", page_icon="🐦🔥")
st.title("🐦🔥 Phoenix Autonomous Agent")

# Initialize agent once
if "agent" not in st.session_state:
    with st.spinner("Initializing Phoenix Services..."):
        init_phoenix()
        # Use a bridge to run async startup in streamlit
        loop = asyncio.new_event_loop()
        loop.run_until_complete(startup_phoenix())
        st.session_state.agent = Agent()

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            loop = asyncio.new_event_loop()
            response = loop.run_until_complete(st.session_state.agent.run(prompt))
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
```

#### **B. Tkinter (Standard Desktop GUI)**
For a lightweight desktop application.

```python
import tkinter as tk
from tkinter import scrolledtext
import asyncio
import threading
from phoenix import init_phoenix, startup_phoenix
from phoenix.agent import Agent

class PhoenixApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🐦🔥 Phoenix AI Agent")
        
        # UI Elements
        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)
        self.chat_area.pack(padx=10, pady=10)
        
        self.entry = tk.Entry(root, width=40)
        self.entry.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.send_btn = tk.Button(root, text="Send", command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        # Background Initialization
        threading.Thread(target=self.init_agent, daemon=True).start()

    def init_agent(self):
        asyncio.run(self._async_init())
        self.agent = Agent()
        self.root.after(0, lambda: self.chat_area.insert(tk.END, "System: Phoenix AI Ready.\n\n"))

    async def _async_init(self):
        init_phoenix()
        await startup_phoenix()

    def send_message(self):
        text = self.entry.get()
        if not text: return
        
        self.chat_area.insert(tk.END, f"You: {text}\n")
        self.entry.delete(0, tk.END)
        
        # Run agent in a separate thread to keep UI responsive
        threading.Thread(target=self.run_agent, args=(text,), daemon=True).start()

    def run_agent(self, prompt):
        response = asyncio.run(self.agent.run(prompt))
        self.root.after(0, lambda: self.chat_area.insert(tk.END, f"Phoenix: {response}\n\n"))

if __name__ == "__main__":
    root = tk.Tk()
    app = PhoenixApp(root)
    root.mainloop()
```

---

## 🧠 Advanced: Hybrid Memory

The Agent uses `HybridMemory`, which manages:
*   **Short-Term**: Recent conversation turns.
*   **Long-Term**: Semantic retrieval from the Vector DB.
*   **Session**: Persistent state for the current objective.
*   **Reflection**: Insights and corrections learned during the loop.

This ensures the agent remains context-aware even during long, multi-step tasks.
