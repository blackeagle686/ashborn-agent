import * as vscode from "vscode";
import * as path from "path";
import * as cp from "child_process";
import { AgentClient } from "./agentClient";
import { AshbornViewProvider } from "./panel";
import { ContextCollector } from "./contextCollector";

let _serverProcess: cp.ChildProcess | undefined;
let _statusBar: vscode.StatusBarItem;
let _provider: AshbornViewProvider;

// ── Activate ──────────────────────────────────────────────────────────────────
export async function activate(ctx: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration("ashborn");
  const port: number = config.get("serverPort") ?? 8765;
  const autoStart: boolean = config.get("autoStartServer") ?? true;

  // Status bar
  _statusBar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100
  );
  _statusBar.command = "ashborn.startServer";
  ctx.subscriptions.push(_statusBar);

  // Core services
  const client = new AgentClient(port);
  const collector = new ContextCollector();
  _provider = new AshbornViewProvider(ctx.extensionUri, client, collector);

  // Register sidebar WebView
  ctx.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      AshbornViewProvider.viewType,
      _provider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  // Register commands
  ctx.subscriptions.push(
    vscode.commands.registerCommand("ashborn.startServer", () =>
      startServer(ctx, port)
    ),
    vscode.commands.registerCommand("ashborn.stopAgent", () =>
      _provider.stop()
    ),
    vscode.commands.registerCommand("ashborn.resetSession", () =>
      _provider.reset()
    ),
    vscode.commands.registerCommand("ashborn.runAgent", async () => {
      const task = await vscode.window.showInputBox({
        prompt: "Describe what you want Ashborn to do",
        placeHolder: "e.g. Add unit tests for the auth module",
      });
      if (task) {
        // Trigger via the panel's internal run
        (_provider as any)._runAgent(task, "plan");
      }
    })
  );

  // ── Layout Enforcement ───────────────────────────────────────────────────
  // We force the Ashborn view to the secondary sidebar (right) on startup
  // This overrides VS Code's tendency to merge views or hide the bar.
  const enforceLayout = async () => {
    try {
      // 1. Focus the view (this opens the panel if hidden)
      await vscode.commands.executeCommand("ashborn.chatView.focus");
      
      // 2. Ensure the panel is actually visible and on the right
      await vscode.commands.executeCommand("workbench.action.focusPanel");
    } catch (e) {
      // Ignore if commands aren't supported in this version
    }
  };

  // Run layout enforcement shortly after activation
  setTimeout(enforceLayout, 2000);

  // Watch for .ashborn-focus file to pop open the sidebar reliably
  const focusWatcher = vscode.workspace.createFileSystemWatcher("**/.ashborn-focus");
  const handleFocus = async (uri: vscode.Uri) => {
    await enforceLayout();
    try { await vscode.workspace.fs.delete(uri); } catch {}
  };
  focusWatcher.onDidCreate(handleFocus);
  focusWatcher.onDidChange(handleFocus);
  ctx.subscriptions.push(focusWatcher);

  // Check if file already exists on startup
  vscode.workspace.findFiles(".ashborn-focus", null, 1).then(files => {
    if (files.length > 0) handleFocus(files[0]);
  });

  // Auto-start server
  if (autoStart) {
    const ready = await client.healthCheck();
    if (!ready) {
      await startServer(ctx, port);
    } else {
      setStatus("ready", port);
    }
  } else {
    setStatus("stopped", port);
  }

  // Open the Ashborn Dashboard if no editors are open
  if (vscode.window.visibleTextEditors.length === 0) {
    showDashboard(ctx);
  }
}

function showDashboard(ctx: vscode.ExtensionContext) {
  const panel = vscode.window.createWebviewPanel(
    "ashborn.dashboard",
    "Ashborn",
    vscode.ViewColumn.One,
    { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(ctx.extensionUri, "media")] }
  );

  const iconUri = panel.webview.asWebviewUri(vscode.Uri.joinPath(ctx.extensionUri, "media", "icon.svg"));

  panel.webview.html = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          background: radial-gradient(circle at 50% 50%, #1a0f2e 0%, #08080c 100%);
          color: white;
          height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-family: sans-serif;
          margin: 0;
          overflow: hidden;
        }
        .logo { width: 200px; height: 200px; animation: pulse 4s infinite ease-in-out; }
        @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; } }
        h1 { margin-top: 20px; font-weight: 200; letter-spacing: 4px; color: #9d38c6; }
        .hint { margin-top: 40px; color: #6b6b80; font-size: 0.9em; }
        kbd { background: #333; padding: 2px 6px; border-radius: 4px; color: #fff; }
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
export function deactivate() {
  if (_serverProcess) {
    _serverProcess.kill();
    _serverProcess = undefined;
  }
}

// ── Server lifecycle ──────────────────────────────────────────────────────────
async function startServer(ctx: vscode.ExtensionContext, port: number) {
  if (_serverProcess) {
    vscode.window.showInformationMessage("Ashborn server is already running.");
    return;
  }

  const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

  // The global installation path of Ashborn Agent
  const ASHBORN_DIR = "/home/tlk/Documents/Projects/my_AItools/ashborn-agent";

  const config = vscode.workspace.getConfiguration("ashborn");
  const venvRel: string = config.get("venvPath") ?? "venv";
  const venvPath = path.isAbsolute(venvRel)
    ? venvRel
    : path.join(ASHBORN_DIR, venvRel);
  const python = path.join(venvPath, "bin", "python3");

  setStatus("starting", port);
  vscode.window.showInformationMessage("🔥 Starting Ashborn Agent server…");

  _serverProcess = cp.spawn(
    python,
    ["-m", "uvicorn", "ashborn.server:app", "--host", "127.0.0.1", "--port", String(port), "--log-level", "warning"],
    { cwd: ASHBORN_DIR, stdio: ["ignore", "pipe", "pipe"] }
  );

  _serverProcess.stdout?.on("data", (d: Buffer) =>
    console.log("[ashborn-server]", d.toString().trim())
  );
  _serverProcess.stderr?.on("data", (d: Buffer) =>
    console.error("[ashborn-server]", d.toString().trim())
  );
  _serverProcess.on("exit", (code) => {
    console.log(`[ashborn-server] exited with code ${code}`);
    _serverProcess = undefined;
    setStatus("stopped", port);
  });

  // Poll until ready (max 30 s)
  const client = new AgentClient(port);
  let attempts = 0;
  const poll = setInterval(async () => {
    attempts++;
    const ok = await client.healthCheck();
    if (ok) {
      clearInterval(poll);
      setStatus("ready", port);
      vscode.window.showInformationMessage("✅ Ashborn Agent is ready!");
    } else if (attempts > 120) {
      clearInterval(poll);
      setStatus("error", port);
      vscode.window.showErrorMessage(
        "❌ Ashborn server failed to start (timed out after 120s). Check the Output panel."
      );
    }
  }, 1000);
}

function setStatus(state: "starting" | "ready" | "stopped" | "error", port: number) {
  const icons: Record<string, string> = {
    starting: "$(loading~spin)",
    ready: "$(flame)",
    stopped: "$(circle-slash)",
    error: "$(error)",
  };
  const labels: Record<string, string> = {
    starting: "Ashborn: starting…",
    ready: `Ashborn :${port}`,
    stopped: "Ashborn: offline",
    error: "Ashborn: error",
  };
  _statusBar.text = `${icons[state]} ${labels[state]}`;
  _statusBar.tooltip = `Ashborn Agent Server — port ${port} — ${state}`;
  _statusBar.show();
}
