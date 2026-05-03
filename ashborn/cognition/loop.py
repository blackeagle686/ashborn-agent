from phoenix.framework.agent.core.loop import AgentLoop
import json
import os
import asyncio

from .helpers.tasks import TASK_FILE, _load_tasks, _mark_task, _reset_failed_tasks
from .helpers.plan import _get_pending_plan_steps, _get_executable_plan_steps, _mark_plan_step, _reset_failed_plan_steps, PLAN_FILE
from .helpers.state import _load_state, _save_state, _init_state_from_tasks, _update_state, _clear_state, STATE_FILE

# ... (omitting top part since I need to use multi_replace to be precise)
from .helpers.generation import GENERATION_FILE
from .helpers.observability import log_agent_action, clear_logs
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

    def _get_executable_tasks(self) -> list:
        try:
            data = _load_tasks()
            all_tasks = data.get("tasks", [])
            task_status_map = {t.get("id"): t.get("status") for t in all_tasks}
            
            executable = []
            for t in all_tasks:
                if t.get("status") != "pending":
                    continue
                deps = t.get("dependencies", [])
                deps_met = True
                deps_failed = False
                for d in deps:
                    s = task_status_map.get(d, "done")
                    if s == "failed":
                        deps_failed = True
                    elif s != "done":
                        deps_met = False
                
                if deps_failed:
                    _mark_task(t.get("id"), "failed")
                    continue
                
                if deps_met:
                    executable.append(t)
                    
            return sorted(executable, key=lambda t: t.get("priority", 99))
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
                    # Use the direct 'edits' list if provided, fallback to 'code' if it happens to be valid JSON
                    chunks = art.get("edits")
                    if not chunks and "code" in art:
                        try:
                            if isinstance(art["code"], str):
                                chunks = json.loads(art["code"])
                            else:
                                chunks = art["code"]
                        except:
                            chunks = []
                    
                    if not chunks:
                        continue # Skip empty updates
                    
                    if is_vscode:
                        # surgical local update still best for VS Code
                        actions.append({
                            "tool": "file_update_multi", 
                            "kwargs": {
                                "file_path": art.get("path", ""), 
                                "edits": chunks
                            }
                        })
                    else:
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

    def _pre_execution_validate(self, actions: list) -> list:
        """Checks for dangerous or malformed actions before execution."""
        errors = []
        for act in actions:
            tool = act.get("tool")
            kwargs = act.get("kwargs", {})
            
            # 1. Path Safety
            path = kwargs.get("path") or kwargs.get("file_path")
            if path:
                if path.startswith("/") or ".." in path:
                    errors.append(f"Safety Violation: Path '{path}' is absolute or contains '..'")
            
            # 2. Command Safety
            if tool in ["terminal", "vscode_terminal_run"]:
                cmd = kwargs.get("command", "")
                forbidden = ["rm -rf /", "mkfs", "dd if="] # Simple examples
                for f in forbidden:
                    if f in cmd:
                        errors.append(f"Safety Violation: Command '{cmd}' contains forbidden pattern '{f}'")
        return errors

    async def run(self, prompt: str, memory, session_id: str, mode: str = "auto", **kwargs) -> str:
        clear_logs()
        is_resume = prompt.strip().lower() == "resume" or mode == "resume"

        if mode == "fast_ans" and not is_resume:
            context = await memory.get_full_context(session_id, query=prompt)
            system_prompt = "You are ASHBORN. Give a concise, direct answer to the user's question."
            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}"
            ans = await self.planner.llm.generate(full_prompt, session_id=session_id)
            await memory.add_interaction(session_id, "assistant", ans)
            return ans

        # 1. Think
        if is_resume:
            log_agent_action("loop", "resume_execution", {}, {"status": "resuming"}, "success")
            _reset_failed_tasks()
            _reset_failed_plan_steps()
            objective_meta = "Resuming previous task list..."
        else:
            _clear_state()
            objective_meta = await self.thinker.analyze(prompt, memory, session_id)
            log_agent_action("thinker", "analyze_prompt", {"prompt": prompt}, objective_meta, "success")
            
            # Initialize execution state from new tasks
            try:
                tasks_data = _load_tasks()
                _init_state_from_tasks(tasks_data.get("tasks", []))
            except Exception:
                pass

        memory.session.set("current_objective", objective_meta)

        if not is_resume:
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
                log_agent_action("planner", "generate_plan_steps", {"task": task}, {"plan_steps": pending_steps}, "success")
                
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
                    
                    if any(b.get("status") == "syntax_error" for b in blocks):
                        error_msg = next((b.get("error") for b in blocks if b.get("status") == "syntax_error"), "Syntax validation failed")
                        log_agent_action("generator", "generate_step", {"step": step, "task": task}, {"error": error_msg}, "failed")
                        reflection = await self.reflector.reflect(step.get("solution", {}).get("approach", ""), {"actions": []}, f"Generation failed: {error_msg}")
                        log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", "")}, reflection, "success")
                        
                        accumulated_results += f"\nStep '{step.get('type')}' (attempt {attempt + 1}):\n  Result: Syntax Error\n  Reflection: {reflection['reflection']}\n"
                        self._schedule_background(memory.add_interaction(session_id, "system", f"Step: {step.get('type')} | Result: Syntax Error | Reflection: {reflection['reflection']}"))
                        continue
                        
                    log_agent_action("generator", "generate_step", {"step": step, "task": task}, gen_data, "success")
                    
                    # 4. Map to Actions & Execute
                    actions = self._map_artifacts_to_actions(blocks)
                    if not actions:
                        _mark_plan_step(step_id, "done")
                        step_success = True
                        break
                        
                    action_result = await self.actor.execute({"actions": actions})
                    log_agent_action("actor", "execute_actions", {"actions": actions}, {"result": action_result}, "success")
                    total_actions += len(actions)
                    
                    # 5. Reflect
                    reflection = await self.reflector.reflect(step.get("solution", {}).get("approach", ""), {"actions": actions}, action_result)
                    log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", ""), "actions": actions, "result": action_result}, reflection, "success")
                    
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
                _update_state(task_id, "failed", task.get('title'))
                task_summaries.append(f"✗ [{task.get('priority')}] {task.get('title')}: failed at step {step_id}")
            else:
                _mark_task(task_id, "done")
                _update_state(task_id, "done", task.get('title'))
                task_summaries.append(f"✓ [{task.get('priority')}] {task.get('title')}")

        # Cleanup only on full success
        all_done = True
        try:
            tasks_data = _load_tasks()
            if any(t.get("status") != "done" for t in tasks_data.get("tasks", [])):
                all_done = False
        except:
            all_done = False

        if all_done:
            for file in [TASK_FILE, PLAN_FILE, GENERATION_FILE, STATE_FILE]:
                if os.path.exists(file):
                    try: os.remove(file)
                    except Exception: pass

        summary = "\n".join(task_summaries) if task_summaries else "No tasks were executed."
        final_answer = f"**Ashborn Task Execution Complete**\n\n{summary}\n\n---\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
        return final_answer

    async def run_stream(self, prompt: str, memory, session_id: str, mode: str = "auto", **kwargs):
        clear_logs()
        is_resume = prompt.strip().lower() == "resume" or mode == "resume"

        if mode == "fast_ans" and not is_resume:
            yield {"type": "status", "role": "analyzer", "content": "⚡ Fast Answer mode active..."}
            context = await memory.get_full_context(session_id, query=prompt)
            system_prompt = "You are ASHBORN. Give a concise, direct answer to the user's question."
            full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser: {prompt}"
            async for chunk in self.planner.llm.generate_stream(full_prompt, session_id=session_id):
                yield {"type": "chunk", "content": chunk}
            await memory.add_interaction(session_id, "assistant", "Fast answer generated.")
            return

        if is_resume:
            yield {"type": "status", "role": "system", "content": "🔄 Resuming previous execution state..."}
            _reset_failed_tasks()
            _reset_failed_plan_steps()
            objective_meta = "Resuming previous task list..."
        else:
            yield {"type": "status", "role": "thinker", "content": "🧠 Decomposing your request into tasks..."}
            _clear_state()
            analyze_task = asyncio.create_task(self.analyzer.analyze_workspace(prompt))
            objective_meta = await self.thinker.analyze(prompt, memory, session_id)
            log_agent_action("thinker", "analyze_prompt", {"prompt": prompt}, objective_meta, "success")
            
            # Initialize execution state from new tasks
            try:
                tasks_data = _load_tasks()
                _init_state_from_tasks(tasks_data.get("tasks", []))
            except Exception:
                pass
                
            try:
                analysis = await asyncio.wait_for(analyze_task, timeout=5.0)
                memory.session.set("project_analysis", analysis)
            except Exception:
                pass

        memory.session.set("current_objective", objective_meta)
        yield {"type": "status", "role": "thinker", "content": "📋 Tasks Breakdown Complete"}
        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")

        accumulated_results = ""
        task_summaries = []
        total_actions = 0
        task_number = 0

        while self._has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            executable_tasks = self._get_executable_tasks()
            if not executable_tasks:
                pending = self._get_pending_tasks()
                if pending:
                    yield {"type": "chunk", "role": "system", "content": "\n⚠ Deadlock: Tasks are pending but dependencies are not met.\n"}
                break
                
            task = executable_tasks[0]
            task_id = task.get("id")
            task_number += 1
            
            try: all_tasks_count = len(_load_tasks().get("tasks", []))
            except Exception: all_tasks_count = "?"

            yield {"type": "status", "role": "planner", "content": f"⚙ Task {task_number}/{all_tasks_count}: {task.get('title')}"}
            yield {"type": "chunk", "role": "planner", "content": f"\n**[P{task.get('priority')}] {task.get('title')}**\n"}

            pending_steps = _get_pending_plan_steps(task_id)
            if not pending_steps:
                yield {"type": "status", "role": "planner", "content": f"  ↳ Generating Plan Steps..."}
                await self.planner.generate_plan_steps(task)
                pending_steps = _get_pending_plan_steps(task_id)
                log_agent_action("planner", "generate_plan_steps", {"task": task}, {"plan_steps": pending_steps}, "success")
                
            if not pending_steps:
                _mark_task(task_id, "done")
                yield {"type": "chunk", "role": "planner", "content": "  ↳ No steps required.\n"}
                continue
                
            task_failed = False
            step_attempts = {} # plan_step_id -> attempt_count
            
            while True:
                executable_steps = _get_executable_plan_steps(task_id)
                if not executable_steps:
                    pending = _get_pending_plan_steps(task_id)
                    if pending:
                        task_failed = True # Deadlock or failed deps
                    break
                    
                to_run = []
                for s in executable_steps:
                    sid = s.get("plan_step_id")
                    step_attempts[sid] = step_attempts.get(sid, 0) + 1
                    if step_attempts[sid] > self.MAX_RETRIES_PER_TASK:
                        _mark_plan_step(sid, "failed")
                        task_failed = True
                    else:
                        to_run.append(s)
                        
                if task_failed or not to_run:
                    break
                    
                yield {"type": "status", "role": "actor", "content": f"  ↳ Generating Code ({len(to_run)} step(s) in parallel)..."}
                
                # Parallel Generation
                gen_coroutines = [self.generator.generate_step(s, task) for s in to_run]
                gen_results = await asyncio.gather(*gen_coroutines, return_exceptions=True)
                
                # Sequential Execution
                for step, gen_data in zip(to_run, gen_results):
                    step_id = step.get("plan_step_id")
                    
                    if isinstance(gen_data, Exception):
                        yield {"type": "chunk", "role": "system", "content": f"    ↳ ⚠ Generator error: {gen_data}\n"}
                        continue
                        
                    yield {"type": "chunk", "role": "planner", "content": f"  ↳ Step {step.get('step_index', '?')} ({step.get('type')}): {step.get('solution', {}).get('approach', '')[:60]}...\n"}
                        
                    blocks = gen_data.get("generation_blocks", [])
                    if any(b.get("status") == "syntax_error" for b in blocks):
                        error_msg = next((b.get("error") for b in blocks if b.get("status") == "syntax_error"), "Syntax validation failed")
                        log_agent_action("generator", "generate_step", {"step": step, "task": task}, {"error": error_msg}, "failed")
                        reflection = await self.reflector.reflect(step.get("solution", {}).get("approach", ""), {"actions": []}, f"Generation failed: {error_msg}")
                        log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", "")}, reflection, "success")
                        
                        accumulated_results += f"\nStep '{step.get('type')}':\nResult: Syntax Error\nReflection: {reflection['reflection']}\n"
                        self._schedule_background(memory.add_interaction(session_id, "system", f"Step: {step.get('type')} | Result: Syntax Error | Reflection: {reflection['reflection']}"))
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ⚠ Retry: Syntax error detected before execution: {reflection['reflection']}\n"}
                        continue
                        
                    log_agent_action("generator", "generate_step", {"step": step, "task": task}, gen_data, "success")
                    actions = self._map_artifacts_to_actions(blocks)
                    
                    if not actions:
                        _mark_plan_step(step_id, "done")
                        yield {"type": "chunk", "role": "actor", "content": f"    ↳ Done (No actions needed)\n"}
                        continue
                        
                    yield {"type": "status", "role": "actor", "content": f"  ↳ Executing {len(actions)} actions..."}
                    action_result = await self.actor.execute({"actions": actions})
                    log_agent_action("actor", "execute_actions", {"actions": actions}, {"result": action_result}, "success")
                    total_actions += len(actions)
                    
                    reflection = await self.reflector.reflect(step.get("solution", {}).get("approach", ""), {"actions": actions}, action_result)
                    log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", ""), "actions": actions, "result": action_result}, reflection, "success")
                    
                    accumulated_results += (f"\nStep '{step.get('type')}':\nResult: {action_result}\nReflection: {reflection['reflection']}\n")
                    self._schedule_background(memory.add_interaction(session_id, "system", f"Step: {step.get('type')} | Result: {action_result} | Reflection: {reflection['reflection']}"))
                    
                    if reflection["is_complete"]:
                        _mark_plan_step(step_id, "done")
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ✓ {reflection['reflection']}\n"}
                    else:
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ⚠ Retry: {reflection['reflection']}\n"}

            if task_failed:
                _mark_task(task_id, "failed")
                _update_state(task_id, "failed", task.get('title'))
                task_summaries.append(f"✗ {task.get('title')}")
                yield {"type": "chunk", "role": "reflector", "content": f"  ↳ ✗ Task failed.\n"}
            else:
                _mark_task(task_id, "done")
                _update_state(task_id, "done", task.get('title'))
                task_summaries.append(f"✓ {task.get('title')}")
                yield {"type": "chunk", "role": "reflector", "content": f"  ↳ ✓ Task complete.\n"}

        # Cleanup only on full success
        all_done = True
        try:
            tasks_data = _load_tasks()
            if any(t.get("status") != "done" for t in tasks_data.get("tasks", [])):
                all_done = False
        except:
            all_done = False

        if all_done:
            yield {"type": "status", "content": "🗑 Cleaning up files..."}
            for file in [TASK_FILE, PLAN_FILE, GENERATION_FILE, STATE_FILE]:
                if os.path.exists(file):
                    try: os.remove(file)
                    except Exception: pass

        summary_lines = "\n".join(task_summaries) if task_summaries else "No tasks were executed."
        yield {"type": "chunk", "content": f"\n\n---\n**All tasks complete!**\n\n{summary_lines}\n"}

        final_answer = f"Tasks complete:\n{summary_lines}\n\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
