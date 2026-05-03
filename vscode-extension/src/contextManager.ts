import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";

export interface Context {
  openFiles: string[];
  activeFile?: {
    path: string;
    language: string;
    content: string;
    selection?: string;
    cursorLine: number;
    cursorCharacter: number;
  };
  fileTree?: string;
  diagnostics?: {
    file: string;
    message: string;
    line: number;
    severity: string;
  }[];
  gitDiff?: string;
}

export class ContextManager {
  private _context: Context = {
    openFiles: [],
  };
  private _updateTimeout?: NodeJS.Timeout;

  constructor() {
    this.refresh();
  }

  public getContext(): Context {
    return this._context;
  }

  /**
   * Manually trigger a refresh of all context data.
   */
  public async refresh() {
    this.update({
      openFiles: this._getOpenFiles(),
      activeFile: this._getActiveFile(),
      diagnostics: this._getDiagnostics(),
      fileTree: await this._getFileTree(),
      gitDiff: await this._getGitDiff(),
    });
  }

  /**
   * Debounced update to keep the context state current.
   */
  public update(partial: Partial<Context>) {
    this._context = { ...this._context, ...partial };
    
    if (this._updateTimeout) clearTimeout(this._updateTimeout);
    this._updateTimeout = setTimeout(() => {
      console.log("ASHBORN CTX UPDATED");
    }, 500);
  }

  public serialize(): string {
    const parts: string[] = [];
    const ctx = this._context;

    // 1. Critical: Active File & Cursor
    if (ctx.activeFile) {
      // Truncate content to ~4000 chars to save tokens while keeping context
      const content = ctx.activeFile.content.length > 4000 
        ? ctx.activeFile.content.slice(0, 2000) + "\n\n[... content truncated ...]\n\n" + ctx.activeFile.content.slice(-2000)
        : ctx.activeFile.content;

      parts.push(`[ACTIVE_FILE]
Path: ${ctx.activeFile.path}
Lang: ${ctx.activeFile.language}
Cursor: L${ctx.activeFile.cursorLine}:C${ctx.activeFile.cursorCharacter}
Content:
\`\`\`
${content}
\`\`\``);
      
      if (ctx.activeFile.selection) {
        parts.push(`[SELECTED_CODE]\n${ctx.activeFile.selection}`);
      }
    }

    // 2. High Priority: Workspace Errors
    if (ctx.diagnostics && ctx.diagnostics.length > 0) {
      parts.push(`[DIAGNOSTICS]\n${ctx.diagnostics.map(d => `${d.severity}: ${d.file}:${d.line} - ${d.message}`).join("\n")}`);
    }

    // 3. Medium Priority: Git State
    if (ctx.gitDiff) {
      parts.push(`[GIT_DIFF]\n${ctx.gitDiff.slice(0, 2000)}`);
    }

    // 4. Low Priority: Open Files & Structure
    if (ctx.openFiles.length > 0) {
      parts.push(`[OPEN_TABS]\n${ctx.openFiles.join(", ")}`);
    }

    if (ctx.fileTree) {
      parts.push(`[WORKSPACE_TREE]\n${ctx.fileTree}`);
    }

    return parts.join("\n\n" + "=".repeat(20) + "\n\n");
  }

  public toJSON() {
    return this._context;
  }

  private _getOpenFiles(): string[] {
    return vscode.window.tabGroups.all
      .flatMap((g) => g.tabs)
      .map((t) => (t.input as any)?.uri?.fsPath)
      .filter(Boolean)
      .map(p => vscode.workspace.asRelativePath(p));
  }

  private _getActiveFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return undefined;

    return {
      path: vscode.workspace.asRelativePath(editor.document.uri),
      language: editor.document.languageId,
      content: editor.document.getText(),
      selection: editor.selection.isEmpty ? undefined : editor.document.getText(editor.selection),
      cursorLine: editor.selection.active.line + 1,
      cursorCharacter: editor.selection.active.character + 1
    };
  }

  private _getDiagnostics() {
    const errors: any[] = [];
    vscode.languages.getDiagnostics().forEach(([uri, diags]) => {
      diags
        .filter((d) => d.severity === vscode.DiagnosticSeverity.Error || d.severity === vscode.DiagnosticSeverity.Warning)
        .forEach((d) => {
          errors.push({
            file: vscode.workspace.asRelativePath(uri),
            message: d.message,
            line: d.range.start.line + 1,
            severity: d.severity === vscode.DiagnosticSeverity.Error ? "Error" : "Warning"
          });
        });
    });
    return errors.slice(0, 20); // Cap at 20 most important diagnostics
  }

  private async _getFileTree(): Promise<string> {
    const files = await vscode.workspace.findFiles("**/*", "**/node_modules/**", 150);
    const paths = files.map(f => vscode.workspace.asRelativePath(f));
    return this._buildTreeString(paths);
  }

  private _buildTreeString(paths: string[]): string {
    const tree: any = {};
    paths.forEach(p => {
      const parts = p.split("/");
      let current = tree;
      parts.forEach(part => {
        if (!current[part]) current[part] = {};
        current = current[part];
      });
    });

    const render = (node: any, indent: string = ""): string => {
      let result = "";
      const keys = Object.keys(node).sort();
      keys.forEach((key, i) => {
        const isLast = i === keys.length - 1;
        const connector = isLast ? "└── " : "├── ";
        result += `${indent}${connector}${key}\n`;
        result += render(node[key], indent + (isLast ? "    " : "│   "));
      });
      return result;
    };

    return render(tree);
  }

  private async _getGitDiff(): Promise<string | undefined> {
    try {
      const gitExtension = vscode.extensions.getExtension("vscode.git")?.exports;
      if (gitExtension) {
        const api = gitExtension.getAPI(1);
        const repo = api.repositories[0];
        if (repo) {
          const stagedChanges = await repo.diff(true);
          const unstagedChanges = await repo.diff(false);
          return `STAGED:\n${stagedChanges || "none"}\n\nUNSTAGED:\n${unstagedChanges || "none"}`;
        }
      }
      
      // Fallback to shell command
      const ws = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!ws) return undefined;
      
      const { execSync } = require("child_process");
      const staged = execSync("git diff --cached", { cwd: ws }).toString();
      const unstaged = execSync("git diff", { cwd: ws }).toString();
      return `STAGED (fallback):\n${staged || "none"}\n\nUNSTAGED (fallback):\n${unstaged || "none"}`;
    } catch {
      return undefined;
    }
  }
}
