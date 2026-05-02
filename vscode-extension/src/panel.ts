import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { AgentClient } from "./agentClient";
import { ContextCollector } from "./contextCollector";
import { LoopController } from "./loopController";

export class AshbornViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "ashborn.chatView";

  private _view?: vscode.WebviewView;
  private _sessionId?: string;
  private _loop: LoopController;

  constructor(
    private readonly _extensionUri: vscode.Uri,
    private readonly _client: AgentClient,
    private readonly _ctx: ContextCollector
  ) {
    this._loop = new LoopController(_client, _ctx);
  }

  // ── Called by VS Code when the sidebar view is opened ─────────────────────
  resolveWebviewView(
    view: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = view;

    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(this._extensionUri, "media"),
      ],
    };

    view.webview.html = this._buildHtml(view.webview);

    // Messages from the WebView UI
    view.webview.onDidReceiveMessage((msg) => this._onMessage(msg));
  }

  // ── Public commands wired up in extension.ts ───────────────────────────────
  stop() {
    this._loop.stop();
    this._post({ type: "status", state: "idle", content: "⏹ Stopped." });
  }

  reset() {
    this._loop.stop();
    this._sessionId = undefined;
    this._client.reset().catch(() => undefined);
    this._post({ type: "reset" });
  }

  // ── Handle messages FROM the WebView ──────────────────────────────────────
  private async _onMessage(msg: any) {
    switch (msg.type) {
      case "send":
        await this._runAgent(msg.task, msg.mode ?? "auto");
        break;
      case "stop":
        this.stop();
        break;
      case "reset":
        this.reset();
        break;
      case "getFiles":
        const files = await vscode.workspace.findFiles("**/*", "**/node_modules/**", 1000);
        const relPaths = files.map(f => vscode.workspace.asRelativePath(f));
        this._post({ type: "files", files: relPaths });
        break;
      case "getConfig":
        try {
          const config = await this._client.getConfig();
          this._post({ type: "config", config });
        } catch (err) {
          this._post({ type: "error", content: "Failed to fetch config: " + err });
        }
        break;
      case "saveConfig":
        try {
          const res = await this._client.updateConfig(msg.settings);
          this._post({ type: "configSaved", success: res.status === "ok", message: res.message });
        } catch (err) {
          this._post({ type: "error", content: "Failed to save config: " + err });
        }
        break;
      case "openFile":
        try {
          let filePath: string = msg.path;
          // Resolve relative paths against the workspace root
          if (!path.isAbsolute(filePath)) {
            const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
            if (wsRoot) {
              filePath = path.join(wsRoot, filePath);
            }
          }
          const fileUri = vscode.Uri.file(filePath);
          const fileDoc = await vscode.workspace.openTextDocument(fileUri);
          await vscode.window.showTextDocument(fileDoc, {
            preview: false,
            preserveFocus: true,
            viewColumn: vscode.ViewColumn.One,
          });
        } catch (_err) {
          // silently ignore — file might not exist yet
        }
        break;
      case "theme":
        const workbenchConfig = vscode.workspace.getConfiguration("workbench");

        // Collect every theme contributed by installed extensions
        const allThemes: { label: string; uiTheme: string }[] = [];
        for (const ext of vscode.extensions.all) {
          const contributes = ext.packageJSON?.contributes;
          if (contributes?.themes) {
            for (const t of contributes.themes) {
              if (t.label) {
                allThemes.push({ label: t.label, uiTheme: t.uiTheme || "" });
              }
            }
          }
        }

        // Priority lists: preferred theme names to try first
        const lightPriority = [
          "Light Modern",
          "Default Light Modern",
          "Light+",
          "Default Light+",
          "Light (Visual Studio)",
          "Quiet Light",
          "Solarized Light"
        ];
        const darkPriority = [
          "Dark Modern",
          "Default Dark Modern",
          "Dark+",
          "Default Dark+",
          "Dark (Visual Studio)",
          "One Dark Pro",
          "Monokai",
          "Dracula"
        ];

        let targetTheme: string | undefined;

        if (msg.isLight) {
          // Try priority list first
          targetTheme = lightPriority.find(name =>
            allThemes.some(t => t.label === name)
          );
          // Fall back to any theme with uiTheme "vs" (light) or label containing "light"
          if (!targetTheme) {
            const found = allThemes.find(
              t => t.uiTheme === "vs" || t.label.toLowerCase().includes("light")
            );
            targetTheme = found?.label;
          }
          // Last resort
          if (!targetTheme) { targetTheme = "Light Modern"; }
        } else {
          // Try priority dark list
          targetTheme = darkPriority.find(name =>
            allThemes.some(t => t.label === name)
          );
          // Fall back to any uiTheme "vs-dark"
          if (!targetTheme) {
            const found = allThemes.find(
              t => t.uiTheme === "vs-dark" || t.label.toLowerCase().includes("dark")
            );
            targetTheme = found?.label;
          }
          if (!targetTheme) { targetTheme = "Dark Modern"; }
        }

        await workbenchConfig.update(
          "colorTheme",
          targetTheme,
          vscode.ConfigurationTarget.Global
        );
        vscode.window.showInformationMessage(`Ashborn: Applied theme → "${targetTheme}"`);
        break;
    }
  }

  // ── Send a task to the agent loop ─────────────────────────────────────────
  private async _runAgent(task: string, mode: string) {
    if (this._loop.isRunning) {
      vscode.window.showWarningMessage("Ashborn is already running. Stop it first.");
      return;
    }

    this._post({ type: "user_message", content: task });

    const newSession = await this._loop.run(
      task,
      this._sessionId,
      mode,
      (evt) => this._post(evt)
    );

    if (newSession) this._sessionId = newSession;
  }

  // ── Send a message TO the WebView ─────────────────────────────────────────
  private _post(msg: object) {
    this._view?.webview.postMessage(msg);
  }

  // ── Build the WebView HTML ─────────────────────────────────────────────────
  private _buildHtml(webview: vscode.Webview): string {
    const mediaUri = (file: string) =>
      webview.asWebviewUri(
        vscode.Uri.joinPath(this._extensionUri, "media", file)
      );

    const cssUri = mediaUri("style.css");
    const jsUri = mediaUri("ui.js");

    // Read the HTML template and inject URIs + CSP nonce
    const htmlPath = path.join(
      this._extensionUri.fsPath,
      "media",
      "ui.html"
    );
    let html = fs.readFileSync(htmlPath, "utf-8");

    html = html
      .replace(/<meta http-equiv="Content-Security-Policy" [^>]*>/i, 
        `<meta http-equiv="Content-Security-Policy" content="default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;">`)
      .replace(/\{\{CSS_URI\}\}/g, cssUri.toString())
      .replace(/\{\{JS_URI\}\}/g, jsUri.toString())
      .replace(/\{\{ASHBORN_ICON_URI\}\}/g, mediaUri("ashborn.png").toString())
      .replace(/\{\{PHOENIX_AI_ICON_URI\}\}/g, mediaUri("phx-nobg.png").toString());

    return html;
  }
}
