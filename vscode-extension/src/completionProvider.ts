import * as vscode from 'vscode';
import { AgentClient } from './agentClient';

export class AshbornCompletionProvider implements vscode.InlineCompletionItemProvider {
  private _client: AgentClient;
  private _debounceTimer: NodeJS.Timeout | null = null;

  constructor(client: AgentClient) {
    this._client = client;
  }

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionItem[] | vscode.InlineCompletionList | null | undefined> {
    
    // Only trigger automatically on typing or explicit invoke
    if (context.triggerKind !== vscode.InlineCompletionTriggerKind.Invoke && 
        context.triggerKind !== vscode.InlineCompletionTriggerKind.Automatic) {
        return null;
    }

    return new Promise((resolve) => {
      if (this._debounceTimer) {
        clearTimeout(this._debounceTimer);
      }

      this._debounceTimer = setTimeout(async () => {
        if (token.isCancellationRequested) {
          resolve(null);
          return;
        }

        const filePath = document.uri.fsPath;
        const offset = document.offsetAt(position);
        const text = document.getText();
        
        const contentBefore = text.substring(0, offset);
        const contentAfter = text.substring(offset);

        try {
          const completion = await this._client.getCompletion(
            filePath,
            contentBefore,
            contentAfter
          );

          if (token.isCancellationRequested || !completion) {
            resolve(null);
            return;
          }

          console.log(`Ashborn Completion: ${completion}`);
          const item = new vscode.InlineCompletionItem(completion, new vscode.Range(position, position));
          resolve([item]);
        } catch (e) {
          console.error(`Ashborn Completion Error: ${e}`);
          resolve(null);
        }
      }, 500); // 500ms debounce
    });
  }
}
