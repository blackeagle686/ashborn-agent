import * as vscode from "vscode";
import { AgentClient } from "./agentClient";
import { ContextCollector } from "./contextCollector";

export type LoopEventCallback = (event: {
  type: "status" | "chunk" | "done" | "error";
  content?: string;
  state?: string;
}) => void;

/**
 * Orchestrates the autonomous agent loop.
 * Collects context → sends task → streams response → optionally repeats.
 */
export class LoopController {
  private _running = false;
  private _stepCount = 0;

  constructor(
    private readonly _client: AgentClient,
    private readonly _context: ContextCollector,
    private readonly _maxSteps = 10
  ) {}

  get isRunning() {
    return this._running;
  }

  stop() {
    this._running = false;
    this._client.abort();
  }

  async run(
    task: string,
    sessionId: string | undefined,
    mode: string,
    onEvent: LoopEventCallback
  ): Promise<string | undefined> {
    if (this._running) return;
    this._running = true;
    this._stepCount = 0;

    // Prepend workspace context and resolve @mentions
    const mentionCtx = await this._resolveMentions(task);
    const workspaceCtx = this._context.collect();
    
    let fullTask = task;
    if (mentionCtx) {
      fullTask += `\n\n---\n[Attached Files Content]\n${mentionCtx}`;
    }
    if (workspaceCtx) {
      fullTask += `\n\n---\n[Workspace Context]\n${workspaceCtx}`;
    }

    onEvent({ type: "status", state: "thinking", content: "🧠 Thinking…" });

    let newSessionId = sessionId;

    try {
      await this._client.sendMessage(
        fullTask,
        sessionId,
        mode,
        async (evt: any) => {
          if (!this._running) return;

          if (evt.type === "session") {
            newSessionId = evt.session_id;
          } else if (evt.type === "vscode_tool") {
            const result = await this._handleVscodeTool(evt.tool, evt.arguments);
            await this._client.sendToolResult(evt.call_id, result);
          } else if (evt.type === "status") {
            this._stepCount++;
            onEvent({
              type: "status",
              state: "executing",
              content: evt.content,
            });
          } else if (evt.type === "chunk") {
            onEvent({ type: "chunk", content: evt.content });
          } else if (evt.type === "done") {
            onEvent({ type: "status", state: "idle" });
            onEvent({ type: "done" });
          } else if (evt.type === "error") {
            onEvent({ type: "error", content: evt.content });
          }
        }
      );
    } catch (e: any) {
      if (this._running) {
        onEvent({ type: "error", content: e.message ?? "Unknown error" });
      }
    } finally {
      this._running = false;
    }

    return newSessionId;
  }

  private async _handleVscodeTool(tool: string, args: any): Promise<string> {
    if (tool === "search") {
      return await this._searchWorkspace(args.query, args.is_regex, args.include, args.exclude);
    }
    return `ERROR: Unknown VS Code tool: ${tool}`;
  }

  private async _searchWorkspace(query: string, isRegex: boolean, include?: string, exclude?: string): Promise<string> {
    const results: string[] = [];
    try {
      await (vscode.workspace as any).findTextInFiles(
        { pattern: query, isRegExp: isRegex },
        { 
          include: include || undefined,
          exclude: exclude || undefined,
          maxResults: 50 
        },
        (result: any) => {
          const relPath = vscode.workspace.asRelativePath(result.uri);
          results.push(`FILE: ${relPath}`);
          result.results.forEach((res: any) => {
            if ('range' in res) {
              const line = res.range.start.line + 1;
              const preview = res.preview.text.trim();
              results.push(`  L${line}: ${preview}`);
            }
          });
        }
      );
      return results.join('\n') || "No results found.";
    } catch (err: any) {
      return `ERROR during search: ${err.message}`;
    }
  }
}
