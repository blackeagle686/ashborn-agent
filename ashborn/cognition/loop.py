from phoenix.framework.agent.core.loop import AgentLoop
import asyncio

from .helpers.tasks import _load_tasks, _mark_task
from .helpers.plan import _get_pending_plan_steps, _mark_plan_step
from .helpers.observability import clear_logs
from .brains.generator import AshbornGenerator
from .core.utils import (
    get_pending_tasks, get_executable_tasks, has_task_file,
    cleanup_state_files, is_all_done,
    init_phase, ensure_plan_steps, execute_step,
    fast_answer, fast_answer_stream, finalize_task,
    validate_and_execute, stream_task_steps, StepResult,
)


class AshbornLoop(AgentLoop):
    """
    Task-file driven agent loop:
      Thinker → Planner → Generator → Actor.
    """

    MAX_RETRIES = 2
    MAX_ACTIONS = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "components") and "generator" in self.components:
            self.generator = self.components["generator"]
        else:
            self.generator = AshbornGenerator(self.planner.llm)

    @property
    def _ctx(self):
        """Bundle components into a dict for utility functions."""
        return dict(
            thinker=self.thinker, planner=self.planner, generator=self.generator,
            reflector=self.reflector, actor=self.actor, analyzer=self.analyzer,
            llm=self.planner.llm, bg=self._background_tasks, retries=self.MAX_RETRIES,
        )

    # ------------------------------------------------------------------
    # Non-streaming
    # ------------------------------------------------------------------

    async def run(self, prompt: str, memory, session_id: str, mode: str = "auto", **kw) -> str:
        clear_logs()
        ctx = self._ctx
        is_resume = prompt.strip().lower() == "resume" or mode == "resume"

        if mode == "fast_ans" and not is_resume:
            return await fast_answer(ctx, prompt, memory, session_id)

        obj = await init_phase(ctx, prompt, memory, session_id, is_resume)
        await memory.add_interaction(session_id, "system", f"Task breakdown: {obj}")

        results, summaries, total = "", [], 0

        while has_task_file() and total < self.MAX_ACTIONS:
            pending = get_pending_tasks()
            if not pending:
                break
            task, tid = pending[0], pending[0].get("id")

            steps = await ensure_plan_steps(ctx, task, tid)
            if not steps:
                _mark_task(tid, "done")
                continue

            failed = False
            for step in steps:
                sid = step.get("plan_step_id")
                ok, txt, cnt = await execute_step(ctx, step, task, memory, session_id)
                total += cnt
                results += txt
                if ok:
                    _mark_plan_step(sid, "done")
                else:
                    _mark_plan_step(sid, "failed")
                    failed = True
                    break

            finalize_task(tid, task, failed, summaries)

        if is_all_done():
            cleanup_state_files()

        summary = "\n".join(summaries) or "No tasks were executed."
        answer = f"**Ashborn Task Execution Complete**\n\n{summary}\n\n---\n{results.strip()}"
        await memory.add_interaction(session_id, "assistant", answer)
        return answer

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def run_stream(self, prompt: str, memory, session_id: str, mode: str = "auto", **kw):
        clear_logs()
        ctx = self._ctx
        is_resume = prompt.strip().lower() == "resume" or mode == "resume"

        if mode == "fast_ans" and not is_resume:
            async for ev in fast_answer_stream(ctx, prompt, memory, session_id):
                yield ev
            return

        yield {"type": "status", "role": "system" if is_resume else "thinker",
               "content": "🔄 Resuming..." if is_resume else "🧠 Decomposing your request..."}

        obj = await init_phase(ctx, prompt, memory, session_id, is_resume)
        memory.session.set("current_objective", obj)
        yield {"type": "status", "role": "thinker", "content": "📋 Tasks Breakdown Complete"}
        await memory.add_interaction(session_id, "system", f"Task breakdown: {obj}")

        results, summaries, total, task_num = "", [], 0, 0

        while has_task_file() and total < self.MAX_ACTIONS:
            executable = get_executable_tasks()
            if not executable:
                if get_pending_tasks():
                    yield {"type": "chunk", "role": "system", "content": "\n⚠ Deadlock\n"}
                break

            task, tid = executable[0], executable[0].get("id")
            task_num += 1

            try:
                count = len(_load_tasks().get("tasks", []))
            except Exception:
                count = "?"

            yield {"type": "status", "role": "planner",
                   "content": f"⚙ Task {task_num}/{count}: {task.get('title')}"}
            yield {"type": "chunk", "role": "planner",
                   "content": f"\n**[P{task.get('priority')}] {task.get('title')}**\n"}

            # Delegate step processing to async generator
            sr = StepResult()
            async for ev in stream_task_steps(ctx, task, tid, memory, session_id, sr):
                yield ev

            total += sr.action_count
            results += sr.text
            finalize_task(tid, task, sr.failed, summaries)

            icon, msg = ("✗", "Task failed.") if sr.failed else ("✓", "Task complete.")
            yield {"type": "chunk", "role": "reflector", "content": f"  ↳ {icon} {msg}\n"}

        if is_all_done():
            yield {"type": "status", "content": "🗑 Cleaning up..."}
            cleanup_state_files()

        summary = "\n".join(summaries) or "No tasks were executed."
        yield {"type": "chunk", "content": f"\n\n---\n**All tasks complete!**\n\n{summary}\n"}
        await memory.add_interaction(session_id, "assistant",
                                     f"Tasks complete:\n{summary}\n\n{results.strip()}")
