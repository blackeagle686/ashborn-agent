import * as vscode from "vscode";
import * as path from "path";

/**
 * Executes structured actions emitted by the agent.
 * All file-edit actions show a diff preview before applying.
 */
export class ActionExecutor {
  async createFile(filePath: string, content: string): Promise<void> {
    const uri = vscode.Uri.file(filePath);
    const bytes = Buffer.from(content, "utf-8");
    await vscode.workspace.fs.writeFile(uri, bytes);
    await vscode.window.showTextDocument(uri, { preview: false });
  }

  async editFile(filePath: string, newContent: string): Promise<boolean> {
    const uri = vscode.Uri.file(filePath);

    // Write proposed content to a temp file and open a diff view
    const tmpUri = uri.with({ path: uri.path + ".ashborn.proposed" });
    const bytes = Buffer.from(newContent, "utf-8");
    await vscode.workspace.fs.writeFile(tmpUri, bytes);

    const answer = await vscode.window.showInformationMessage(
      `Ashborn wants to edit: ${path.basename(filePath)}`,
      { modal: false },
      "Show Diff & Accept",
      "Reject"
    );

    if (answer === "Show Diff & Accept") {
      await vscode.commands.executeCommand(
        "vscode.diff",
        uri,
        tmpUri,
        `Ashborn Edit — ${path.basename(filePath)} (original ↔ proposed)`
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
        return true;
      }
    }
    // Reject — clean up temp file
    await vscode.workspace.fs.delete(tmpUri).then(undefined, () => undefined);
    return false;
  }

  async deleteFile(filePath: string): Promise<boolean> {
    const answer = await vscode.window.showWarningMessage(
      `Ashborn wants to DELETE: ${path.basename(filePath)}`,
      { modal: true },
      "Delete",
      "Cancel"
    );
    if (answer === "Delete") {
      await vscode.workspace.fs.delete(vscode.Uri.file(filePath));
      return true;
    }
    return false;
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
