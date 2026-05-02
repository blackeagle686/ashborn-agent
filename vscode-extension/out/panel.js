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
exports.AshbornViewProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const loopController_1 = require("./loopController");
class AshbornViewProvider {
    constructor(_extensionUri, _client, _ctx) {
        this._extensionUri = _extensionUri;
        this._client = _client;
        this._ctx = _ctx;
        this._loop = new loopController_1.LoopController(_client, _ctx);
    }
    // ── Called by VS Code when the sidebar view is opened ─────────────────────
    resolveWebviewView(view, _context, _token) {
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
    async _onMessage(msg) {
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
                }
                catch (err) {
                    this._post({ type: "error", content: "Failed to fetch config: " + err });
                }
                break;
            case "saveConfig":
                try {
                    const res = await this._client.updateConfig(msg.settings);
                    this._post({ type: "configSaved", success: res.status === "ok", message: res.message });
                }
                catch (err) {
                    this._post({ type: "error", content: "Failed to save config: " + err });
                }
                break;
            case "openFile":
                try {
                    let filePath = msg.path;
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
                }
                catch (_err) {
                    // silently ignore — file might not exist yet
                }
                break;
            case "theme":
                const workbenchConfig = vscode.workspace.getConfiguration("workbench");
                const theme = msg.isLight ? "Default Light Modern" : "Default Dark Modern";
                await workbenchConfig.update("colorTheme", theme, vscode.ConfigurationTarget.Global);
                break;
        }
    }
    // ── Send a task to the agent loop ─────────────────────────────────────────
    async _runAgent(task, mode) {
        if (this._loop.isRunning) {
            vscode.window.showWarningMessage("Ashborn is already running. Stop it first.");
            return;
        }
        this._post({ type: "user_message", content: task });
        const newSession = await this._loop.run(task, this._sessionId, mode, (evt) => this._post(evt));
        if (newSession)
            this._sessionId = newSession;
    }
    // ── Send a message TO the WebView ─────────────────────────────────────────
    _post(msg) {
        this._view?.webview.postMessage(msg);
    }
    // ── Build the WebView HTML ─────────────────────────────────────────────────
    _buildHtml(webview) {
        const mediaUri = (file) => webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, "media", file));
        const cssUri = mediaUri("style.css");
        const jsUri = mediaUri("ui.js");
        // Read the HTML template and inject URIs + CSP nonce
        const htmlPath = path.join(this._extensionUri.fsPath, "media", "ui.html");
        let html = fs.readFileSync(htmlPath, "utf-8");
        html = html
            .replace(/<meta http-equiv="Content-Security-Policy" [^>]*>/i, `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src ${webview.cspSource} 'unsafe-inline'; img-src ${webview.cspSource} data:; media-src * data: blob:; connect-src * ws: wss:;">`)
            .replace(/\{\{CSS_URI\}\}/g, cssUri.toString())
            .replace(/\{\{JS_URI\}\}/g, jsUri.toString())
            .replace(/\{\{ASHBORN_ICON_URI\}\}/g, mediaUri("ashborn.png").toString())
            .replace(/\{\{PHOENIX_AI_ICON_URI\}\}/g, mediaUri("phx-nobg.png").toString());
        return html;
    }
}
exports.AshbornViewProvider = AshbornViewProvider;
AshbornViewProvider.viewType = "ashborn.chatView";
//# sourceMappingURL=panel.js.map