from phoenix.framework.agent.core.loop import AgentLoop
import json
import os
import asyncio

from .helpers.tasks import TASK_FILE, _load_tasks, _mark_task
from .helpers.plan import _get_pending_plan_steps, _mark_plan_step, PLAN_FILE
from .helpers.generation import GENERATION_FILE
from .generator import AshbornGenerator

class AshbornLoop(AgentLoop):
    """
    Task-file driven agent loop with intermediate Plan and Generation phases:
      1. Thinker -> Tasks (ashborn_tasks.json)
      2. Planner -> Plan Steps for current Task (ashborn.plan.json)
      3. Generator -> Generation blocks mapping to actions (ashborn.generation.json)
      4. Actor -> Executes tools without LLM.
    """

    MAX_RETRIES_PER_TASK = 2
    MAX_TOTAL_ACTIONS = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fetch the generator injected by the Agent, fallback to instantiating directly
        if hasattr(self, "components") and "generator" in self.components:
            self.generator = self.components["generator"]
        else:
            self.generator = AshbornGenerator(self.planner.llm)

    def _schedule_background(self, coro):
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        def _on_done(t):
            self._background_tasks.discard(t)
            try:
                _ = t.exception()
            except Exception:
                pass
        task.add_done_callback(_on_done)

    def _get_pending_tasks(self) -> list:
        try:
            data = _load_tasks()
            return sorted(
                [t for t in data.get("tasks", []) if t.get("status") == "pending"],
                key=lambda t: t.get("priority", 99)
            )
        except Exception:
            return []

    def _has_task_file(self) -> bool:
        return os.path.exists(TASK_FILE)

    def _map_artifacts_to_actions(self, generation_blocks: list) -> list:
        try:
            from ashborn.server import vscode_ipc_context
            is_vscode = vscode_ipc_context.get() is not None
        except ImportError:
            is_vscode = False
            
        actions = []
        for block in generation_blocks:
            for art in block.get("artifacts", []):
                if art["type"] == "file_write":
                    if is_vscode:
                        actions.append({"tool": "vscode_create_file", "kwargs": {"path": art.get("path", ""), "content": art.get("code", "")}})
                    else:
                        actions.append({"tool": "file_write", "kwargs": {"file_path": art.get("path", ""), "content": art.get("code", "")}})
                elif art["type"] == "file_update_multi":
                    try:
                        chunks = json.loads(art.get("code", "[]")) if isinstance(art.get("code"), str) else art.get("code", [])
                    except:
                        chunks = []
                    
                    if is_vscode:
                        # VS Code extension currently handles full file edits via "edit_file" 
                        # We might need to map chunks back to full string or just pass the chunks if the extension supports it.
                        # Wait, vscode_edit_file_tool takes `content`. 
                        # If we have chunks, we should probably apply them locally or use the local tool.
                        # Actually, let's use the local file_update_multi for surgical precision even in VS Code, 
                        # since the VS Code extension file watcher will pick up the local file changes immediately!
                        # The only downside is no "diff review" popup.
                        actions.append({
                            "tool": "file_update_multi", 
                            "kwargs": {
                                "file_path": art.get("path", ""), 
                                "edits": chunks
                            }
                        })
                elif art["type"] == "terminal":
                    if is_vscode:
                        actions.append({"tool": "vscode_terminal_run", "kwargs": {"command": art.get("code", "")}})
                    else:
                        actions.append({"tool": "terminal", "kwargs": {"command": art.get("code", "")}})
        return actions

    async def run(self, prompt: str, memory, session_id: str, mode: str = "auto", **kwargs) -> str:
        if mode == "fast_ans":
            context = await memory.get_full_context(session_id, query=prompt)
            system_prompt = "You are ASHBORN. Give a concise, direct answer to the user's question."
            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}"
            ans = await self.planner.llm.generate(full_prompt, session_id=session_id)
            await memory.add_interaction(session_id, "assistant", ans)
            return ans

        # 1. Think
        objective_meta = await self.thinker.analyze(prompt, memory, session_id)
        memory.session.set("current_objective", objective_meta)

        try:
            analysis = await self.analyzer.analyze_workspace(prompt)
            memory.session.set("project_analysis", analysis)
        except Exception:
            pass

        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")
        
        accumulated_results = ""
        task_summaries = []
        total_actions = 0

        # Loop Tasks
        while self._has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            pending_tasks = self._get_pending_tasks()
            if not pending_tasks:
                break
            
            task = pending_tasks[0]
            task_id = task.get("id")
            
            # 2. Plan (Generate plan_steps if none exist for this task)
            pending_steps = _get_pending_plan_steps(task_id)
            if not pending_steps:
                await self.planner.generate_plan_steps(task)
                pending_steps = _get_pending_plan_steps(task_id)
                
            if not pending_steps:
                # No steps generated, mark task done
                _mark_task(task_id, "done")
                continue
                
            task_failed = False
            
            # Loop Plan Steps
            for step in pending_steps:
                step_id = step.get("plan_step_id")
                step_success = False
                
                for attempt in range(self.MAX_RETRIES_PER_TASK):
                    # 3. Generate Code Iteratively
                    gen_data = await self.generator.generate_step(step, task)
                    blocks = gen_data.get("generation_blocks", [])
                    
                    # 4. Map to Actions & Execute
                    actions = self._map_artifacts_to_actions(blocks)
                    if not actions:
                        _mark_plan_step(step_id, "done")
                        step_success = True
                        break
                        
                    action_result = await self.actor.execute({"actions": actions})
                    total_actions += len(actions)
                    
                    # 5. Reflect
                    reflection = await self.reflector.reflect(step.get("solution", {}).get("approach", ""), {"actions": actions}, action_result)
                    
                    accumulated_results += (
                        f"\nStep '{step.get('type')}' (attempt {attempt + 1}):\n"
                        f"  Result: {action_result}\n"
                        f"  Reflection: {reflection['reflection']}\n"
                    )
                    
                    self._schedule_background(memory.add_interaction(
                        session_id, "system",
                        f"Step: {step.get('type')} | Result: {action_result} | Reflection: {reflection['reflection']}"
                    ))
                    
                    if reflection["is_complete"]:
                        _mark_plan_step(step_id, "done")
                        step_success = True
                        break
                
                if not step_success:
                    _mark_plan_step(step_id, "failed")
                    task_failed = True
                    break # Stop step execution for this task
                    
            if task_failed:
                _mark_task(task_id, "failed")
                task_summaries.append(f"✗ [{task.get('priority')}] {task.get('title')}: failed at step {step_id}")
            else:
                _mark_task(task_id, "done")
                task_summaries.append(f"✓ [{task.get('priority')}] {task.get('title')}")

        # Cleanup
        for file in [TASK_FILE, PLAN_FILE, GENERATION_FILE]:
            if os.path.exists(file):
                try: os.remove(file)
                except Exception: pass

        summary = "\n".join(task_summaries) if task_summaries else "No tasks were executed."
        final_answer = f"**Ashborn Task Execution Complete**\n\n{summary}\n\n---\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
        return final_answer

    async def run_stream(self, prompt: str, memory, session_id: str, mode: str = "auto", **kwargs):
        if mode == "fast_ans":
            yield {"type": "status", "role": "analyzer", "content": "⚡ Fast Answer mode active..."}
            context = await memory.get_full_context(session_id, query=prompt)
            system_prompt = "You are ASHBORN. Give a concise, direct answer to the user's question."
            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}"
            async for chunk in self.planner.llm.generate_stream(full_prompt, session_id=session_id):
                yield {"type": "chunk", "content": chunk}
            await memory.add_interaction(session_id, "assistant", "Fast answer generated.")
            return

        yield {"type": "status", "role": "thinker", "content": "🧠 Decomposing your request into tasks..."}
        analyze_task = asyncio.create_task(self.analyzer.analyze_workspace(prompt))
        objective_meta = await self.thinker.analyze(prompt, memory, session_id)
        memory.session.set("current_objective", objective_meta)
        try:
            analysis = await asyncio.wait_for(analyze_task, timeout=5.0)
            memory.session.set("project_analysis", analysis)
        except Exception:
            pass

        yield {"type": "status", "role": "thinker", "content": "📋 Tasks Breakdown Complete"}
        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")

        accumulated_results = ""
        task_summaries = []
        total_actions = 0
        task_number = 0

        while self._has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            pending_tasks = self._get_pending_tasks()
            if not pending_tasks:
                break
                
            task = pending_tasks[0]
            task_id = task.get("id")
            task_number += 1
            
            try: all_tasks_count = len(_load_tasks().get("tasks", []))
            except Exception: all_tasks_count = "?"

            yield {"type": "status", "role": "planner", "content": f"⚙ Task {task_number}/{all_tasks_count}: {task.get('title')}"}
            yield {"type": "chunk", "role": "planner", "content": f"\n**[P{task.get('priority')}] {task.get('title')}**\n"}

            # Planner phase
            pending_steps = _get_pending_plan_steps(task_id)
            if not pending_steps:
                yield {"type": "status", "role": "planner", "content": f"  ↳ Generating Plan Steps..."}
                await self.planner.generate_plan_steps(task)
                pending_steps = _get_pending_plan_steps(task_id)
                
            if not pending_steps:
                _mark_task(task_id, "done")
                yield {"type": "chunk", "role": "planner", "content": "  ↳ No steps required.\n"}
                continue
                
            task_failed = False
            
            for step in pending_steps:
                step_id = step.get("plan_step_id")
                yield {"type": "chunk", "role": "planner", "content": f"  ↳ Step {step.get('step_index', '?')} ({step.get('type')}): {step.get('solution', {}).get('approach', '')[:60]}...\n"}
                
                step_success = False
                for attempt in range(self.MAX_RETRIES_PER_TASK):
                    yield {"type": "status", "role": "actor", "content": f"  ↳ Generating Code (Attempt {attempt+1})..."}
                    gen_data = await self.generator.generate_step(step, task)
                    blocks = gen_data.get("generation_blocks", [])
                    actions = self._map_artifacts_to_actions(blocks)
                    
                    if not actions:
                        _mark_plan_step(step_id, "done")
                        step_success = True
                        yield {"type": "chunk", "role": "actor", "content": f"    ↳ Done (No actions needed)\n"}
                        break
                        
                    yield {"type": "status", "role": "actor", "content": f"  ↳ Executing {len(actions)} actions..."}
                    action_result = await self.actor.execute({"actions": actions})
                    total_actions += len(actions)
                    
                    reflection = await self.reflector.reflect(step.get("solution", {}).get("approach", ""), {"actions": actions}, action_result)
                    
                    accumulated_results += (f"\nStep '{step.get('type')}':\nResult: {action_result}\nReflection: {reflection['reflection']}\n")
                    self._schedule_background(memory.add_interaction(session_id, "system", f"Step: {step.get('type')} | Result: {action_result} | Reflection: {reflection['reflection']}"))
                    
                    if reflection["is_complete"]:
                        _mark_plan_step(step_id, "done")
                        step_success = True
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ✓ {reflection['reflection']}\n"}
                        break
                    else:
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ⚠ Retry: {reflection['reflection']}\n"}
                        
                if not step_success:
                    _mark_plan_step(step_id, "failed")
                    task_failed = True
                    break

            if task_failed:
                _mark_task(task_id, "failed")
                task_summaries.append(f"✗ {task.get('title')}")
                yield {"type": "chunk", "role": "reflector", "content": f"  ↳ ✗ Task failed.\n"}
            else:
                _mark_task(task_id, "done")
                task_summaries.append(f"✓ {task.get('title')}")
                yield {"type": "chunk", "role": "reflector", "content": f"  ↳ ✓ Task complete.\n"}

        yield {"type": "status", "content": "🗑 Cleaning up files..."}
        for file in [TASK_FILE, PLAN_FILE, GENERATION_FILE]:
            if os.path.exists(file):
                try: os.remove(file)
                except Exception: pass

        summary_lines = "\n".join(task_summaries) if task_summaries else "No tasks were executed."
        yield {"type": "chunk", "content": f"\n\n---\n**All tasks complete!**\n\n{summary_lines}\n"}

        final_answer = f"Tasks complete:\n{summary_lines}\n\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
