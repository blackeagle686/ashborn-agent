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
exports.ContextCollector = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class ContextCollector {
    /**
     * Collect relevant workspace context and return it as a formatted string.
     * Injected into the task before sending to the agent.
     */
    collect() {
        const parts = [];
        // 1. Active file
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            const doc = editor.document;
            parts.push(`Active file: ${doc.fileName}`);
            // Selected text
            const sel = editor.selection;
            if (!sel.isEmpty) {
                const selected = doc.getText(sel);
                parts.push(`Selected text:\n\`\`\`\n${selected.slice(0, 800)}\n\`\`\``);
            }
        }
        // 2. Open file list
        const openFiles = vscode.window.tabGroups.all
            .flatMap((g) => g.tabs)
            .map((t) => t.input?.uri?.fsPath)
            .filter(Boolean)
            .slice(0, 10);
        if (openFiles.length > 0) {
            parts.push(`Open files:\n${openFiles.map((f) => `  - ${f}`).join("\n")}`);
        }
        // 3. Workspace diagnostics (errors only)
        const errors = [];
        vscode.languages.getDiagnostics().forEach(([uri, diags]) => {
            diags
                .filter((d) => d.severity === vscode.DiagnosticSeverity.Error)
                .slice(0, 5)
                .forEach((d) => {
                errors.push(`  ${path.basename(uri.fsPath)}:${d.range.start.line + 1} — ${d.message}`);
            });
        });
        if (errors.length > 0) {
            parts.push(`Errors in workspace:\n${errors.join("\n")}`);
        }
        // 4. File tree (workspace root, depth-1)
        const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (ws) {
            try {
                const entries = fs.readdirSync(ws).filter((e) => !e.startsWith(".") &&
                    !["node_modules", "venv", "__pycache__", "out"].includes(e));
                parts.push(`Workspace root (${path.basename(ws)}):\n${entries.map((e) => `  ${e}`).join("\n")}`);
            }
            catch {
                /* ignore */
            }
        }
        return parts.join("\n\n");
    }
}
exports.ContextCollector = ContextCollector;
//# sourceMappingURL=contextCollector.js.map