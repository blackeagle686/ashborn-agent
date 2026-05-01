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
exports.ActionExecutor = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
/**
 * Executes structured actions emitted by the agent.
 * All file-edit actions show a diff preview before applying.
 */
class ActionExecutor {
    async createFile(filePath, content) {
        const uri = vscode.Uri.file(filePath);
        const bytes = Buffer.from(content, "utf-8");
        await vscode.workspace.fs.writeFile(uri, bytes);
        await vscode.window.showTextDocument(uri, { preview: false });
    }
    async editFile(filePath, newContent) {
        const uri = vscode.Uri.file(filePath);
        // Write proposed content to a temp file and open a diff view
        const tmpUri = uri.with({ path: uri.path + ".ashborn.proposed" });
        const bytes = Buffer.from(newContent, "utf-8");
        await vscode.workspace.fs.writeFile(tmpUri, bytes);
        const answer = await vscode.window.showInformationMessage(`Ashborn wants to edit: ${path.basename(filePath)}`, { modal: false }, "Show Diff & Accept", "Reject");
        if (answer === "Show Diff & Accept") {
            await vscode.commands.executeCommand("vscode.diff", uri, tmpUri, `Ashborn Edit — ${path.basename(filePath)} (original ↔ proposed)`);
            const confirm = await vscode.window.showInformationMessage("Apply this change?", { modal: true }, "Accept", "Reject");
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
    async deleteFile(filePath) {
        const answer = await vscode.window.showWarningMessage(`Ashborn wants to DELETE: ${path.basename(filePath)}`, { modal: true }, "Delete", "Cancel");
        if (answer === "Delete") {
            await vscode.workspace.fs.delete(vscode.Uri.file(filePath));
            return true;
        }
        return false;
    }
    async runCommand(command) {
        let terminal = vscode.window.terminals.find((t) => t.name === "Ashborn Agent");
        if (!terminal) {
            terminal = vscode.window.createTerminal("Ashborn Agent");
        }
        terminal.show(true);
        terminal.sendText(command);
    }
}
exports.ActionExecutor = ActionExecutor;
//# sourceMappingURL=actionExecutor.js.map