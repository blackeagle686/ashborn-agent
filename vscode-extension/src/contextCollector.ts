import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

export class ContextCollector {
  /**
   * Collect relevant workspace context and return it as a formatted string.
   * Injected into the task before sending to the agent.
   */
  collect(): string {
    const parts: string[] = [];

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
      .map((t) => (t.input as any)?.uri?.fsPath)
      .filter(Boolean)
      .slice(0, 10);

    if (openFiles.length > 0) {
      parts.push(`Open files:\n${openFiles.map((f) => `  - ${f}`).join("\n")}`);
    }

    // 3. Workspace diagnostics (errors only)
    const errors: string[] = [];
    vscode.languages.getDiagnostics().forEach(([uri, diags]) => {
      diags
        .filter((d) => d.severity === vscode.DiagnosticSeverity.Error)
        .slice(0, 5)
        .forEach((d) => {
          errors.push(
            `  ${path.basename(uri.fsPath)}:${d.range.start.line + 1} — ${d.message}`
          );
        });
    });
    if (errors.length > 0) {
      parts.push(`Errors in workspace:\n${errors.join("\n")}`);
    }

    // 4. File tree (workspace root, depth-1)
    const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (ws) {
      try {
        const entries = fs.readdirSync(ws).filter(
          (e) =>
            !e.startsWith(".") &&
            !["node_modules", "venv", "__pycache__", "out"].includes(e)
        );
        parts.push(`Workspace root (${path.basename(ws)}):\n${entries.map((e) => `  ${e}`).join("\n")}`);
      } catch {
        /* ignore */
      }
    }

    return parts.join("\n\n");
  }
}
