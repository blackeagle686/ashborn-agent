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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const cp = __importStar(require("child_process"));
const http = __importStar(require("http"));
const agentClient_1 = require("./agentClient");
const panel_1 = require("./panel");
const contextCollector_1 = require("./contextCollector");
const completionProvider_1 = require("./completionProvider");
const codeActionProvider_1 = require("./codeActionProvider");
let _serverProcess;
let _statusBar;
let _provider;
// ── Activate ──────────────────────────────────────────────────────────────────
async function activate(ctx) {
    const config = vscode.workspace.getConfiguration("ashborn");
    const port = config.get("serverPort") ?? 8765;
    const autoStart = config.get("autoStartServer") ?? true;
    // Status bar
    _statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    _statusBar.command = "ashborn.startServer";
    ctx.subscriptions.push(_statusBar);
    // Core services
    const client = new agentClient_1.AgentClient(port);
    const collector = new contextCollector_1.ContextCollector();
    _provider = new panel_1.AshbornViewProvider(ctx.extensionUri, client, collector);
    // Register sidebar WebView
    ctx.subscriptions.push(vscode.window.registerWebviewViewProvider(panel_1.AshbornViewProvider.viewType, _provider, { webviewOptions: { retainContextWhenHidden: true } }));
    // Register Inline Completion Provider
    const completionProvider = new completionProvider_1.AshbornCompletionProvider(client);
    ctx.subscriptions.push(vscode.languages.registerInlineCompletionItemProvider([{ pattern: '**/*' }, { scheme: 'untitled' }], // Apply to all files
    completionProvider));
    // Register Code Action Provider
    ctx.subscriptions.push(vscode.languages.registerCodeActionsProvider([{ pattern: '**/*' }, { scheme: 'untitled' }], new codeActionProvider_1.AshbornCodeActionProvider(), { providedCodeActionKinds: codeActionProvider_1.AshbornCodeActionProvider.providedCodeActionKinds }));
    // Helper to run code actions
    const executeAction = async (actionStr, document, range) => {
        let editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        // Handle cases where VS Code passes a Uri instead of TextDocument (Context Menu)
        const doc = (document && "getText" in document) ? document : editor.document;
        const sel = (range && "start" in range) ? range : editor.selection;
        if (sel.isEmpty) {
            vscode.window.showInformationMessage("Please select some code first.");
            return;
        }
        const selectedText = doc.getText(sel);
        const fullText = doc.getText();
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `Ashborn: Executing ${actionStr}...`,
            cancellable: false
        }, async (progress) => {
            try {
                const result = await client.executeCodeAction(actionStr, doc.uri.fsPath, selectedText, fullText);
                if (!result) {
                    vscode.window.showErrorMessage("Ashborn: Failed to generate result.");
                    return;
                }
                if (actionStr === "explain") {
                    // Ensure sidebar is visible
                    await vscode.commands.executeCommand('ashborn-sidebar.focus');
                    _provider.postMessage({ type: "user_message", content: `Explain selected code in ${path.basename(doc.uri.fsPath)}:` });
                    _provider.postMessage({ type: "chunk", content: result });
                    _provider.postMessage({ type: "done" });
                }
                else {
                    const edit = new vscode.WorkspaceEdit();
                    edit.replace(doc.uri, sel, result);
                    await vscode.workspace.applyEdit(edit);
                }
            }
            catch (err) {
                vscode.window.showErrorMessage(`Ashborn: Error executing action: ${err}`);
            }
        });
    };
    // Register commands
    ctx.subscriptions.push(vscode.commands.registerCommand("ashborn.action.explain", (d, r) => executeAction("explain", d, r)), vscode.commands.registerCommand("ashborn.action.refactor", (d, r) => executeAction("refactor", d, r)), vscode.commands.registerCommand("ashborn.action.optimize", (d, r) => executeAction("optimize", d, r)), vscode.commands.registerCommand("ashborn.action.fix", (d, r) => executeAction("fix", d, r)), vscode.commands.registerCommand("ashborn.startServer", () => startServer(ctx, port)), vscode.commands.registerCommand("ashborn.stopAgent", () => _provider.stop()), vscode.commands.registerCommand("ashborn.resetSession", () => _provider.reset()), vscode.commands.registerCommand("ashborn.runAgent", async () => {
        const task = await vscode.window.showInputBox({
            prompt: "Describe what you want Ashborn to do",
            placeHolder: "e.g. Add unit tests for the auth module",
        });
        if (task) {
            // Trigger via the panel's internal run
            _provider._runAgent(task, "plan");
        }
    }));
    // ── Layout Enforcement ───────────────────────────────────────────────────
    // We force the Ashborn view to the secondary sidebar (right) on startup
    // This overrides VS Code's tendency to merge views or hide the bar.
    const enforceLayout = async () => {
        try {
            // 1. Focus the view (this opens the panel if hidden)
            await vscode.commands.executeCommand("ashborn.chatView.focus");
            // 2. Ensure the panel is actually visible and on the right
            await vscode.commands.executeCommand("workbench.action.focusPanel");
        }
        catch (e) {
            // Ignore if commands aren't supported in this version
        }
    };
    // Run layout enforcement shortly after activation
    setTimeout(enforceLayout, 2000);
    // Watch for .ashborn-focus file to pop open the sidebar reliably
    const focusWatcher = vscode.workspace.createFileSystemWatcher("**/.ashborn-focus");
    const handleFocus = async (uri) => {
        await enforceLayout();
        try {
            await vscode.workspace.fs.delete(uri);
        }
        catch { }
    };
    focusWatcher.onDidCreate(handleFocus);
    focusWatcher.onDidChange(handleFocus);
    ctx.subscriptions.push(focusWatcher);
    // Check if file already exists on startup
    vscode.workspace.findFiles(".ashborn-focus", null, 1).then(files => {
        if (files.length > 0)
            handleFocus(files[0]);
    });
    // Auto-start server
    if (autoStart) {
        const ready = await client.healthCheck();
        if (!ready) {
            await startServer(ctx, port);
        }
        else {
            setStatus("ready", port);
        }
    }
    else {
        setStatus("stopped", port);
    }
    // Open the Ashborn Dashboard if no editors are open
    if (vscode.window.visibleTextEditors.length === 0) {
        showDashboard(ctx);
    }
}
function showDashboard(ctx) {
    const panel = vscode.window.createWebviewPanel("ashborn.dashboard", "Ashborn", vscode.ViewColumn.One, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(ctx.extensionUri, "media")] });
    const iconUri = panel.webview.asWebviewUri(vscode.Uri.joinPath(ctx.extensionUri, "media", "ashborn.png"));
    panel.webview.html = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        :root {
          --bg-dark: radial-gradient(circle at 50% 50%, #1a0f2e 0%, #08080c 100%);
          --bg-light: radial-gradient(circle at 50% 50%, #f7f7fa 0%, #e2e2e8 100%);
        }
        body {
          background: var(--bg-dark);
          color: white;
          height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-family: sans-serif;
          margin: 0;
          overflow: hidden;
          transition: all 0.5s ease;
        }
        body.vscode-light {
          background: var(--bg-light);
          color: #1a1a1a;
        }
        .logo { 
          width: 200px; 
          height: 200px; 
          animation: pulse 4s infinite ease-in-out; 
          filter: drop-shadow(0 0 30px rgba(157, 56, 198, 0.4));
        }
        body.vscode-light .logo {
          filter: drop-shadow(0 0 30px rgba(157, 56, 198, 0.2));
        }
        @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; } }
        h1 { margin-top: 20px; font-weight: 200; letter-spacing: 4px; color: #9d38c6; }
        .hint { margin-top: 40px; color: #6b6b80; font-size: 0.9em; }
        kbd { background: rgba(128,128,128,0.2); padding: 2px 6px; border-radius: 4px; color: inherit; border: 1px solid rgba(128,128,128,0.3); }
      </style>
    </head>
    <body>
      <img src="${iconUri}" class="logo">
      <h1>ASHBORN</h1>
      <div class="hint">Press <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>I</kbd> to open Chat</div>
    </body>
    </html>
  `;
}
// ── Deactivate ────────────────────────────────────────────────────────────────
function deactivate() {
    if (_serverProcess) {
        _serverProcess.kill();
        _serverProcess = undefined;
    }
}
// ── Server lifecycle ──────────────────────────────────────────────────────────
async function startServer(ctx, port) {
    if (_serverProcess) {
        vscode.window.showInformationMessage("Ashborn server is already running.");
        return;
    }
    const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    // The global installation path of Ashborn Agent
    const ASHBORN_DIR = "/home/tlk/Documents/Projects/my_AItools/ashborn-agent";
    const config = vscode.workspace.getConfiguration("ashborn");
    const venvRel = config.get("venvPath") ?? "venv";
    const venvPath = path.isAbsolute(venvRel)
        ? venvRel
        : path.join(ASHBORN_DIR, venvRel);
    const python = path.join(venvPath, "bin", "python3");
    setStatus("starting", port);
    vscode.window.showInformationMessage("🔥 Starting Ashborn Agent server…");
    _serverProcess = cp.spawn(python, ["-m", "uvicorn", "ashborn.server:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"], {
        cwd: ws || ASHBORN_DIR,
        env: {
            ...process.env,
            PYTHONPATH: ASHBORN_DIR
        },
        stdio: ["ignore", "pipe", "pipe"]
    });
    _serverProcess.stdout?.on("data", (d) => console.log("[ashborn-server]", d.toString().trim()));
    _serverProcess.stderr?.on("data", (d) => console.error("[ashborn-server]", d.toString().trim()));
    _serverProcess.on("exit", (code) => {
        console.log(`[ashborn-server] exited with code ${code}`);
        _serverProcess = undefined;
        setStatus("stopped", port);
    });
    // Poll until ready (max 30 s)
    const client = new agentClient_1.AgentClient(port);
    let attempts = 0;
    const poll = setInterval(async () => {
        attempts++;
        // Check health
        const status = await new Promise(resolve => {
            const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
                let data = "";
                res.on("data", (c) => (data += c));
                res.on("end", () => {
                    try {
                        resolve(JSON.parse(data));
                    }
                    catch {
                        resolve(null);
                    }
                });
            });
            req.on("error", () => resolve(null));
        });
        if (status && status.status === "ok") {
            if (status.agent_ready) {
                clearInterval(poll);
                setStatus("ready", port);
                vscode.window.showInformationMessage("✅ Ashborn Agent is ready!");
            }
            else {
                setStatus("starting", port);
                _statusBar.text = `$(loading~spin) Ashborn: Loading AI…`;
            }
        }
        else if (attempts > 120) {
            clearInterval(poll);
            setStatus("error", port);
            vscode.window.showErrorMessage("❌ Ashborn server failed to start (timed out after 120s). Check the Output panel.");
        }
    }, 1000);
}
function setStatus(state, port) {
    const icons = {
        starting: "$(loading~spin)",
        ready: "$(flame)",
        stopped: "$(circle-slash)",
        error: "$(error)",
    };
    const labels = {
        starting: "Ashborn: starting…",
        ready: `Ashborn :${port}`,
        stopped: "Ashborn: offline",
        error: "Ashborn: error",
    };
    _statusBar.text = `${icons[state]} ${labels[state]}`;
    _statusBar.tooltip = `Ashborn Agent Server — port ${port} — ${state}`;
    _statusBar.show();
}
//# sourceMappingURL=extension.js.map