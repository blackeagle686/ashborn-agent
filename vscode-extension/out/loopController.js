"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.LoopController = void 0;
const vscode = __importStar(require("vscode"));
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
            await this._client.sendMessage(fullTask, sessionId, mode, async (evt) => {
                if (!this._running)
                    return;
                if (evt.type === "session") {
                    newSessionId = evt.session_id;
                }
                else if (evt.type === "vscode_tool") {
                    const result = await this._handleVscodeTool(evt.tool, evt.arguments);
                    // noop = fire-and-forget, no result needed
                    if (evt.call_id !== "noop") {
                        await this._client.sendToolResult(evt.call_id, result);
                    }
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
    async _handleVscodeTool(tool, args) {
        if (tool === "search") {
            return await this._searchWorkspace(args.query, args.is_regex, args.include, args.exclude);
        }
        if (tool === "open_file") {
            return await this._openFileInEditor(args.path);
        }
        return `ERROR: Unknown VS Code tool: ${tool}`;
    }
    async _openFileInEditor(filePath) {
        try {
            // Resolve relative paths against the workspace root
            if (!require("path").isAbsolute(filePath)) {
                const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
                if (wsRoot)
                    filePath = require("path").join(wsRoot, filePath);
            }
            const uri = vscode.Uri.file(filePath);
            const doc = await vscode.workspace.openTextDocument(uri);
            await vscode.window.showTextDocument(doc, {
                preview: false,
                preserveFocus: true,
                viewColumn: vscode.ViewColumn.One,
            });
            return `opened: ${filePath}`;
        }
        catch (err) {
            return `ERROR opening file: ${err.message}`;
        }
    }
    async _searchWorkspace(query, isRegex, include, exclude) {
        const results = [];
        try {
            await vscode.workspace.findTextInFiles({ pattern: query, isRegExp: isRegex }, {
                include: include || undefined,
                exclude: exclude || undefined,
                maxResults: 50
            }, (result) => {
                const relPath = vscode.workspace.asRelativePath(result.uri);
                results.push(`FILE: ${relPath}`);
                result.results.forEach((res) => {
                    if ('range' in res) {
                        const line = res.range.start.line + 1;
                        const preview = res.preview.text.trim();
                        results.push(`  L${line}: ${preview}`);
                    }
                });
            });
            return results.join('\n') || "No results found.";
        }
        catch (err) {
            return `ERROR during search: ${err.message}`;
        }
    }
    async _resolveMentions(text) {
        const mentions = text.match(/@[\w./\-]+/g);
        if (!mentions)
            return "";
        const results = [];
        const root = vscode.workspace.workspaceFolders?.[0]?.uri;
        if (!root)
            return "";
        for (const mention of mentions) {
            const relPath = mention.substring(1);
            const uri = vscode.Uri.joinPath(root, relPath);
            try {
                const stat = await vscode.workspace.fs.stat(uri);
                if (stat.type === vscode.FileType.File) {
                    const content = await vscode.workspace.fs.readFile(uri);
                    results.push(`FILE: ${relPath}\n\`\`\`\n${content.toString()}\n\`\`\``);
                }
                else if (stat.type === vscode.FileType.Directory) {
                    const files = await vscode.workspace.fs.readDirectory(uri);
                    const list = files.map(([name, type]) => `${type === vscode.FileType.Directory ? 'DIR: ' : 'FILE: '}${name}`).join('\n');
                    results.push(`DIRECTORY: ${relPath}\nCONTENTS:\n${list}`);
                }
            }
            catch {
                // ignore invalid paths
            }
        }
        return results.join('\n\n');
    }
}
exports.LoopController = LoopController;
//# sourceMappingURL=loopController.js.map