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
const agentClient_1 = require("./agentClient");
const panel_1 = require("./panel");
const contextCollector_1 = require("./contextCollector");
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
    // Register commands
    ctx.subscriptions.push(vscode.commands.registerCommand("ashborn.startServer", () => startServer(ctx, port)), vscode.commands.registerCommand("ashborn.stopAgent", () => _provider.stop()), vscode.commands.registerCommand("ashborn.resetSession", () => _provider.reset()), vscode.commands.registerCommand("ashborn.runAgent", async () => {
        const task = await vscode.window.showInputBox({
            prompt: "Describe what you want Ashborn to do",
            placeHolder: "e.g. Add unit tests for the auth module",
        });
        if (task) {
            // Trigger via the panel's internal run
            _provider._runAgent(task, "plan");
        }
    }));
    // Watch for .ashborn-focus file to pop open the sidebar reliably
    const focusWatcher = vscode.workspace.createFileSystemWatcher("**/.ashborn-focus");
    const handleFocus = async (uri) => {
        await vscode.commands.executeCommand("ashborn.chatView.focus");
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
    _serverProcess = cp.spawn(python, ["-m", "uvicorn", "ashborn.server:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"], { cwd: ASHBORN_DIR, stdio: ["ignore", "pipe", "pipe"] });
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
        const ok = await client.healthCheck();
        if (ok) {
            clearInterval(poll);
            setStatus("ready", port);
            vscode.window.showInformationMessage("✅ Ashborn Agent is ready!");
        }
        else if (attempts > 30) {
            clearInterval(poll);
            setStatus("error", port);
            vscode.window.showErrorMessage("❌ Ashborn server failed to start. Check the Output panel.");
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