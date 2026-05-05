from phoenix.framework.agent.core.loop import AgentLoop
import asyncio

from .helpers.tasks import _load_tasks, _mark_task, _reset_failed_tasks
from .helpers.plan import _get_pending_plan_steps, _get_executable_plan_steps, _mark_plan_step, _reset_failed_plan_steps
from .helpers.state import _init_state_from_tasks, _update_state, _clear_state
from .helpers.observability import log_agent_action, clear_logs
from .generator import AshbornGenerator
from .prompts import build_fast_answer_prompt
from .utils import (
    get_pending_tasks, get_executable_tasks, has_task_file,
    map_artifacts_to_actions, pre_execution_validate,
    is_sensitive_action, check_and_ask_approval,
    cleanup_state_files, is_all_done, schedule_background,
)


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

    # ------------------------------------------------------------------
    # Non-streaming entry point
    # ------------------------------------------------------------------

    async def run(self, prompt: str, memory, session_id: str, mode: str = "auto", **kwargs) -> str:
        clear_logs()
        is_resume = prompt.strip().lower() == "resume" or mode == "resume"

        # Fast-answer shortcut
        if mode == "fast_ans" and not is_resume:
            return await self._fast_answer(prompt, memory, session_id)

        # 1. Think / Resume
        objective_meta = await self._init_phase(prompt, memory, session_id, is_resume)
        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")

        accumulated_results = ""
        task_summaries = []
        total_actions = 0

        while has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            pending = get_pending_tasks()
            if not pending:
                break

            task = pending[0]
            task_id = task.get("id")

            # 2. Plan
            pending_steps = await self._ensure_plan_steps(task, task_id)
            if not pending_steps:
                _mark_task(task_id, "done")
                continue

            task_failed = False

            # 3-5. Generate → Execute → Reflect (per step)
            for step in pending_steps:
                step_id = step.get("plan_step_id")
                step_ok, result_text, action_count = await self._execute_step(step, task, memory, session_id)
                total_actions += action_count
                accumulated_results += result_text

                if step_ok:
                    _mark_plan_step(step_id, "done")
                else:
                    _mark_plan_step(step_id, "failed")
                    task_failed = True
                    break

            self._finalize_task(task_id, task, task_failed, task_summaries)

        # Cleanup on full success
        if is_all_done():
            cleanup_state_files()

        summary = "\n".join(task_summaries) or "No tasks were executed."
        final_answer = f"**Ashborn Task Execution Complete**\n\n{summary}\n\n---\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)
        return final_answer

    # ------------------------------------------------------------------
    # Streaming entry point
    # ------------------------------------------------------------------

    async def run_stream(self, prompt: str, memory, session_id: str, mode: str = "auto", **kwargs):
        clear_logs()
        is_resume = prompt.strip().lower() == "resume" or mode == "resume"

        # Fast-answer shortcut
        if mode == "fast_ans" and not is_resume:
            async for event in self._fast_answer_stream(prompt, memory, session_id):
                yield event
            return

        # 1. Think / Resume
        if is_resume:
            yield {"type": "status", "role": "system", "content": "🔄 Resuming previous execution state..."}
        else:
            yield {"type": "status", "role": "thinker", "content": "🧠 Decomposing your request into tasks..."}

        objective_meta = await self._init_phase(prompt, memory, session_id, is_resume)
        memory.session.set("current_objective", objective_meta)
        yield {"type": "status", "role": "thinker", "content": "📋 Tasks Breakdown Complete"}
        await memory.add_interaction(session_id, "system", f"Task breakdown: {objective_meta}")

        accumulated_results = ""
        task_summaries = []
        total_actions = 0
        task_number = 0

        while has_task_file() and total_actions < self.MAX_TOTAL_ACTIONS:
            executable = get_executable_tasks()
            if not executable:
                if get_pending_tasks():
                    yield {"type": "chunk", "role": "system", "content": "\n⚠ Deadlock: Tasks are pending but dependencies are not met.\n"}
                break

            task = executable[0]
            task_id = task.get("id")
            task_number += 1

            try:
                all_tasks_count = len(_load_tasks().get("tasks", []))
            except Exception:
                all_tasks_count = "?"

            yield {"type": "status", "role": "planner", "content": f"⚙ Task {task_number}/{all_tasks_count}: {task.get('title')}"}
            yield {"type": "chunk", "role": "planner", "content": f"\n**[P{task.get('priority')}] {task.get('title')}**\n"}

            # 2. Plan
            pending_steps = _get_pending_plan_steps(task_id)
            if not pending_steps:
                yield {"type": "status", "role": "planner", "content": "  ↳ Generating Plan Steps..."}
                await self.planner.generate_plan_steps(task)
                pending_steps = _get_pending_plan_steps(task_id)
                log_agent_action("planner", "generate_plan_steps", {"task": task}, {"plan_steps": pending_steps}, "success")

            if not pending_steps:
                _mark_task(task_id, "done")
                yield {"type": "chunk", "role": "planner", "content": "  ↳ No steps required.\n"}
                continue

            task_failed = False
            step_attempts = {}

            # 3-5. Step execution loop
            while True:
                exec_steps = _get_executable_plan_steps(task_id)
                if not exec_steps:
                    if _get_pending_plan_steps(task_id):
                        task_failed = True
                    break

                to_run = []
                for s in exec_steps:
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

                gen_results = await asyncio.gather(
                    *[self.generator.generate_step(s, task) for s in to_run],
                    return_exceptions=True,
                )

                for step, gen_data in zip(to_run, gen_results):
                    step_id = step.get("plan_step_id")

                    if isinstance(gen_data, Exception):
                        yield {"type": "chunk", "role": "system", "content": f"    ↳ ⚠ Generator error: {gen_data}\n"}
                        continue

                    yield {"type": "chunk", "role": "planner", "content": f"  ↳ Step {step.get('step_index', '?')} ({step.get('type')}): {step.get('solution', {}).get('approach', '')[:60]}...\n"}

                    blocks = gen_data.get("generation_blocks", [])

                    # Syntax-error retry
                    if any(b.get("status") == "syntax_error" for b in blocks):
                        result_text, reflection = await self._handle_syntax_error(step, task, blocks, memory, session_id)
                        accumulated_results += result_text
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ⚠ Retry: Syntax error detected before execution: {reflection['reflection']}\n"}
                        continue

                    log_agent_action("generator", "generate_step", {"step": step, "task": task}, gen_data, "success")
                    actions = map_artifacts_to_actions(blocks)

                    if not actions:
                        _mark_plan_step(step_id, "done")
                        yield {"type": "chunk", "role": "actor", "content": "    ↳ Done (No actions needed)\n"}
                        continue

                    yield {"type": "status", "role": "actor", "content": f"  ↳ Executing {len(actions)} actions..."}

                    action_result, actions, executed = await self._validate_and_execute(actions)
                    if executed:
                        total_actions += len(actions)

                    if not executed and is_sensitive_action(actions):
                        yield {"type": "chunk", "role": "system", "content": f"    ↳ ⛔ {action_result}\n"}
                    elif not executed:
                        yield {"type": "chunk", "role": "system", "content": f"    ↳ ⚠ Safety Warning: {action_result}\n"}

                    reflection = await self.reflector.reflect(
                        step.get("solution", {}).get("approach", ""), {"actions": actions}, action_result,
                    )
                    log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", ""), "actions": actions, "result": action_result}, reflection, "success")

                    accumulated_results += f"\nStep '{step.get('type')}':\nResult: {action_result}\nReflection: {reflection['reflection']}\n"
                    schedule_background(self._background_tasks, memory.add_interaction(
                        session_id, "system",
                        f"Step: {step.get('type')} | Result: {action_result} | Reflection: {reflection['reflection']}",
                    ))

                    if reflection["is_complete"]:
                        _mark_plan_step(step_id, "done")
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ✓ {reflection['reflection']}\n"}
                    else:
                        yield {"type": "chunk", "role": "reflector", "content": f"    ↳ ⚠ Retry: {reflection['reflection']}\n"}

            # Finalize task
            self._finalize_task(task_id, task, task_failed, task_summaries)
            icon = "✗" if task_failed else "✓"
            msg = "Task failed." if task_failed else "Task complete."
            yield {"type": "chunk", "role": "reflector", "content": f"  ↳ {icon} {msg}\n"}

        # Cleanup on full success
        if is_all_done():
            yield {"type": "status", "content": "🗑 Cleaning up files..."}
            cleanup_state_files()

        summary_lines = "\n".join(task_summaries) or "No tasks were executed."
        yield {"type": "chunk", "content": f"\n\n---\n**All tasks complete!**\n\n{summary_lines}\n"}

        final_answer = f"Tasks complete:\n{summary_lines}\n\n{accumulated_results.strip()}"
        await memory.add_interaction(session_id, "assistant", final_answer)

    # ==================================================================
    # Private helpers (shared by run / run_stream)
    # ==================================================================

    async def _fast_answer(self, prompt, memory, session_id) -> str:
        """Handle fast_ans mode (non-streaming)."""
        context = await memory.get_full_context(session_id, query=prompt)
        full_prompt = build_fast_answer_prompt(context, prompt)
        ans = await self.planner.llm.generate(full_prompt, session_id=session_id)
        await memory.add_interaction(session_id, "assistant", ans)
        return ans

    async def _fast_answer_stream(self, prompt, memory, session_id):
        """Handle fast_ans mode (streaming)."""
        yield {"type": "status", "role": "analyzer", "content": "⚡ Fast Answer mode active..."}
        context = await memory.get_full_context(session_id, query=prompt)
        full_prompt = build_fast_answer_prompt(context, prompt)
        async for chunk in self.planner.llm.generate_stream(full_prompt, session_id=session_id):
            yield {"type": "chunk", "content": chunk}
        await memory.add_interaction(session_id, "assistant", "Fast answer generated.")

    async def _init_phase(self, prompt, memory, session_id, is_resume) -> str:
        """Run the Think phase (or resume). Returns the objective metadata string."""
        if is_resume:
            log_agent_action("loop", "resume_execution", {}, {"status": "resuming"}, "success")
            _reset_failed_tasks()
            _reset_failed_plan_steps()
            return "Resuming previous task list..."

        _clear_state()

        # Fire workspace analysis in the background (streaming uses wait_for)
        analyze_coro = self.analyzer.analyze_workspace(prompt)
        analyze_task = asyncio.create_task(analyze_coro)

        objective_meta = await self.thinker.analyze(prompt, memory, session_id)
        log_agent_action("thinker", "analyze_prompt", {"prompt": prompt}, objective_meta, "success")

        # Initialize execution state from new tasks
        try:
            tasks_data = _load_tasks()
            _init_state_from_tasks(tasks_data.get("tasks", []))
        except Exception:
            pass

        # Wait for workspace analysis (best-effort)
        try:
            analysis = await asyncio.wait_for(analyze_task, timeout=5.0)
            memory.session.set("project_analysis", analysis)
        except Exception:
            pass

        memory.session.set("current_objective", objective_meta)
        return objective_meta

    async def _ensure_plan_steps(self, task, task_id) -> list:
        """Generate plan steps for a task if they don't exist yet."""
        steps = _get_pending_plan_steps(task_id)
        if not steps:
            await self.planner.generate_plan_steps(task)
            steps = _get_pending_plan_steps(task_id)
            log_agent_action("planner", "generate_plan_steps", {"task": task}, {"plan_steps": steps}, "success")
        return steps

    async def _execute_step(self, step, task, memory, session_id) -> tuple[bool, str, int]:
        """
        Run generate → execute → reflect for one step across all retry attempts.
        Returns (success, accumulated_text, action_count).
        """
        result_text = ""
        total_action_count = 0

        for attempt in range(self.MAX_RETRIES_PER_TASK):
            gen_data = await self.generator.generate_step(step, task)
            blocks = gen_data.get("generation_blocks", [])

            # Syntax-error → retry
            if any(b.get("status") == "syntax_error" for b in blocks):
                txt, _ = await self._handle_syntax_error(step, task, blocks, memory, session_id, attempt=attempt)
                result_text += txt
                continue

            log_agent_action("generator", "generate_step", {"step": step, "task": task}, gen_data, "success")
            actions = map_artifacts_to_actions(blocks)

            if not actions:
                return True, result_text, total_action_count

            action_result, actions, executed = await self._validate_and_execute(actions)
            if executed:
                total_action_count += len(actions)

            reflection = await self.reflector.reflect(
                step.get("solution", {}).get("approach", ""), {"actions": actions}, action_result,
            )
            log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", ""), "actions": actions, "result": action_result}, reflection, "success")

            result_text += (
                f"\nStep '{step.get('type')}' (attempt {attempt + 1}):\n"
                f"  Result: {action_result}\n"
                f"  Reflection: {reflection['reflection']}\n"
            )
            schedule_background(self._background_tasks, memory.add_interaction(
                session_id, "system",
                f"Step: {step.get('type')} | Result: {action_result} | Reflection: {reflection['reflection']}",
            ))

            if reflection["is_complete"]:
                return True, result_text, total_action_count

        return False, result_text, total_action_count

    async def _handle_syntax_error(self, step, task, blocks, memory, session_id, attempt=0):
        """Handle syntax-error blocks: log, reflect, return result text + reflection."""
        error_msg = next(
            (b.get("error") for b in blocks if b.get("status") == "syntax_error"),
            "Syntax validation failed",
        )
        log_agent_action("generator", "generate_step", {"step": step, "task": task}, {"error": error_msg}, "failed")

        reflection = await self.reflector.reflect(
            step.get("solution", {}).get("approach", ""), {"actions": []}, f"Generation failed: {error_msg}",
        )
        log_agent_action("reflector", "reflect", {"approach": step.get("solution", {}).get("approach", "")}, reflection, "success")

        result_text = f"\nStep '{step.get('type')}' (attempt {attempt + 1}):\n  Result: Syntax Error\n  Reflection: {reflection['reflection']}\n"
        schedule_background(self._background_tasks, memory.add_interaction(
            session_id, "system",
            f"Step: {step.get('type')} | Result: Syntax Error | Reflection: {reflection['reflection']}",
        ))
        return result_text, reflection

    async def _validate_and_execute(self, actions) -> tuple[str, list, bool]:
        """Validate, get approval, execute. Returns (result_str, final_actions, was_executed)."""
        errors = pre_execution_validate(actions)
        if errors:
            log_agent_action("loop", "pre_execution_validate", {"actions": actions}, {"errors": errors}, "failed")
            return "Pre-execution validation failed: " + "; ".join(errors), actions, False

        approved, actions = await check_and_ask_approval(actions)
        if not approved:
            log_agent_action("loop", "ask_approval", {"actions": actions}, {"result": "denied"}, "failed")
            return "Execution denied by user.", actions, False

        result = await self.actor.execute({"actions": actions})
        log_agent_action("actor", "execute_actions", {"actions": actions}, {"result": result}, "success")
        return result, actions, True

    @staticmethod
    def _finalize_task(task_id, task, failed, summaries):
        """Mark task done/failed and append to summaries list."""
        status = "failed" if failed else "done"
        _mark_task(task_id, status)
        _update_state(task_id, status, task.get("title"))
        icon = "✗" if failed else "✓"
        summaries.append(f"{icon} [{task.get('priority')}] {task.get('title')}")
