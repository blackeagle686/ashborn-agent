import * as vscode from "vscode";
import * as path from "path";

/**
 * Executes structured actions emitted by the agent.
 * All file-edit actions show a diff preview before applying.
 */
export class ActionExecutor {
  /**
   * Validates that the path is within the workspace.
   * Throws an error if the path is outside.
   */
  private _validatePath(filePath: string): string {
    const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!wsRoot) {
      throw new Error("No workspace folder open.");
    }

    const absolutePath = path.isAbsolute(filePath)
      ? filePath
      : path.join(wsRoot, filePath);

    const relative = path.relative(wsRoot, absolutePath);
    if (relative.startsWith("..") || path.isAbsolute(relative)) {
      throw new Error(`Permission denied: Path is outside the workspace: ${filePath}`);
    }

    return absolutePath;
  }

  async createFile(filePath: string, content: string): Promise<string> {
    try {
      const absPath = this._validatePath(filePath);
      const uri = vscode.Uri.file(absPath);
      const bytes = Buffer.from(content, "utf-8");
      
      // Ensure parent directory exists
      const dirUri = vscode.Uri.file(path.dirname(absPath));
      await vscode.workspace.fs.createDirectory(dirUri);
      
      await vscode.workspace.fs.writeFile(uri, bytes);
      await vscode.window.showTextDocument(uri, { preview: false });
      return `Successfully created: ${path.basename(absPath)}`;
    } catch (err: any) {
      return `ERROR creating file: ${err.message}`;
    }
  }

  async editFile(filePath: string, newContent: string): Promise<string> {
    try {
      const absPath = this._validatePath(filePath);
      const uri = vscode.Uri.file(absPath);

      // Write proposed content to a temp file and open a diff view
      const tmpUri = uri.with({ path: uri.path + ".ashborn.proposed" });
      const bytes = Buffer.from(newContent, "utf-8");
      await vscode.workspace.fs.writeFile(tmpUri, bytes);

      const answer = await vscode.window.showInformationMessage(
        `Ashborn wants to edit: ${path.basename(absPath)}`,
        { modal: false },
        "Show Diff & Accept",
        "Reject"
      );

      if (answer === "Show Diff & Accept") {
        await vscode.commands.executeCommand(
          "vscode.diff",
          uri,
          tmpUri,
          `Ashborn Edit — ${path.basename(absPath)} (original ↔ proposed)`
        );
        const confirm = await vscode.window.showInformationMessage(
          "Apply this change?",
          { modal: true },
          "Accept",
          "Reject"
        );
        if (confirm === "Accept") {
          await vscode.workspace.fs.writeFile(uri, bytes);
          await vscode.workspace.fs.delete(tmpUri);
          return `Successfully updated: ${path.basename(absPath)}`;
        }
      }
      // Reject — clean up temp file
      await vscode.workspace.fs.delete(tmpUri).then(undefined, () => undefined);
      return "Edit REJECTED by user.";
    } catch (err: any) {
      return `ERROR editing file: ${err.message}`;
    }
  }

  async deleteFile(filePath: string): Promise<string> {
    try {
      const absPath = this._validatePath(filePath);
      const answer = await vscode.window.showWarningMessage(
        `Ashborn wants to DELETE: ${path.basename(absPath)}`,
        { modal: true },
        "Delete",
        "Cancel"
      );
      if (answer === "Delete") {
        await vscode.workspace.fs.delete(vscode.Uri.file(absPath), { recursive: true });
        return `Successfully deleted: ${path.basename(absPath)}`;
      }
      return "Deletion REJECTED by user.";
    } catch (err: any) {
      return `ERROR deleting file: ${err.message}`;
    }
  }

  async runCommand(command: string): Promise<void> {
    let terminal = vscode.window.terminals.find(
      (t) => t.name === "Ashborn Agent"
    );
    if (!terminal) {
      terminal = vscode.window.createTerminal("Ashborn Agent");
    }
    terminal.show(true);
    terminal.sendText(command);
  }
}
