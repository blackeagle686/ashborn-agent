"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LoopController = void 0;
/**
 * Orchestrates the autonomous agent loop.
 * Collects context → sends task → streams response → optionally repeats.
 */
class LoopController {
    constructor(_client, _context, _maxSteps = 10) {
        this._client = _client;
        this._context = _context;
        this._maxSteps = _maxSteps;
        this._running = false;
        this._stepCount = 0;
    }
    get isRunning() {
        return this._running;
    }
    stop() {
        this._running = false;
        this._client.abort();
    }
    async run(task, sessionId, mode, onEvent) {
        if (this._running)
            return;
        this._running = true;
        this._stepCount = 0;
        // Prepend workspace context
        const ctx = this._context.collect();
        const fullTask = ctx
            ? `${task}\n\n---\n[Workspace Context]\n${ctx}`
            : task;
        onEvent({ type: "status", state: "thinking", content: "🧠 Thinking…" });
        let newSessionId = sessionId;
        try {
            await this._client.sendMessage(fullTask, sessionId, mode, (evt) => {
                if (!this._running)
                    return;
                if (evt.type === "session") {
                    newSessionId = evt.session_id;
                }
                else if (evt.type === "status") {
                    this._stepCount++;
                    onEvent({
                        type: "status",
                        state: "executing",
                        content: evt.content,
                    });
                }
                else if (evt.type === "chunk") {
                    onEvent({ type: "chunk", content: evt.content });
                }
                else if (evt.type === "done") {
                    onEvent({ type: "status", state: "idle" });
                    onEvent({ type: "done" });
                }
                else if (evt.type === "error") {
                    onEvent({ type: "error", content: evt.content });
                }
            });
        }
        catch (e) {
            if (this._running) {
                onEvent({ type: "error", content: e.message ?? "Unknown error" });
            }
        }
        finally {
            this._running = false;
        }
        return newSessionId;
    }
}
exports.LoopController = LoopController;
//# sourceMappingURL=loopController.js.map