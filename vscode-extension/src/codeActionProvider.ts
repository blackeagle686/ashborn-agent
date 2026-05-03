import * as vscode from 'vscode';

export class AshbornCodeActionProvider implements vscode.CodeActionProvider {
  public static readonly providedCodeActionKinds = [
    vscode.CodeActionKind.Refactor,
    vscode.CodeActionKind.QuickFix
  ];

  public provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
    token: vscode.CancellationToken
  ): vscode.CodeAction[] {
    
    // Only show if there's a non-empty selection
    if (range.isEmpty) {
      return [];
    }

    const explainAction = this.createCommandAction("Ashborn: Explain Code", "ashborn.action.explain", document, range);
    const refactorAction = this.createCommandAction("Ashborn: Refactor Code", "ashborn.action.refactor", document, range);
    const optimizeAction = this.createCommandAction("Ashborn: Optimize Performance", "ashborn.action.optimize", document, range);
    const fixAction = this.createCommandAction("Ashborn: Fix Bugs", "ashborn.action.fix", document, range);

    refactorAction.isPreferred = true;

    return [
      explainAction,
      refactorAction,
      optimizeAction,
      fixAction
    ];
  }

  private createCommandAction(
    title: string,
    commandId: string,
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection
  ): vscode.CodeAction {
    const action = new vscode.CodeAction(title, vscode.CodeActionKind.Refactor);
    action.command = {
      command: commandId,
      title: title,
      // When invoked via Code Action lightbulb, arguments are passed to the command
      arguments: [document, range]
    };
    return action;
  }
}
