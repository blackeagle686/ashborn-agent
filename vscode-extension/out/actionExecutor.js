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
    constructor() {
        this._terminalWriteEmitter = new vscode.EventEmitter();
    }
    /**
     * Validates that the path is within the workspace.
     * Throws an error if the path is outside.
     */
    _validatePath(filePath) {
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
    async createFile(filePath, content) {
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
        }
        catch (err) {
            return `ERROR creating file: ${err.message}`;
        }
    }
    async editFile(filePath, newContent) {
        try {
            const absPath = this._validatePath(filePath);
            const uri = vscode.Uri.file(absPath);
            // Write proposed content to a temp file and open a diff view
            const tmpUri = uri.with({ path: uri.path + ".ashborn.proposed" });
            const bytes = Buffer.from(newContent, "utf-8");
            await vscode.workspace.fs.writeFile(tmpUri, bytes);
            const answer = await vscode.window.showInformationMessage(`Ashborn wants to edit: ${path.basename(absPath)}`, { modal: false }, "Show Diff & Accept", "Reject");
            if (answer === "Show Diff & Accept") {
                await vscode.commands.executeCommand("vscode.diff", uri, tmpUri, `Ashborn Edit — ${path.basename(absPath)} (original ↔ proposed)`);
                const confirm = await vscode.window.showInformationMessage("Apply this change?", { modal: true }, "Accept", "Reject");
                if (confirm === "Accept") {
                    await vscode.workspace.fs.writeFile(uri, bytes);
                    await vscode.workspace.fs.delete(tmpUri);
                    return `Successfully updated: ${path.basename(absPath)}`;
                }
            }
            // Reject — clean up temp file
            await vscode.workspace.fs.delete(tmpUri).then(undefined, () => undefined);
            return "Edit REJECTED by user.";
        }
        catch (err) {
            return `ERROR editing file: ${err.message}`;
        }
    }
    async deleteFile(filePath) {
        try {
            const absPath = this._validatePath(filePath);
            const answer = await vscode.window.showWarningMessage(`Ashborn wants to DELETE: ${path.basename(absPath)}`, { modal: true }, "Delete", "Cancel");
            if (answer === "Delete") {
                await vscode.workspace.fs.delete(vscode.Uri.file(absPath), { recursive: true });
                return `Successfully deleted: ${path.basename(absPath)}`;
            }
            return "Deletion REJECTED by user.";
        }
        catch (err) {
            return `ERROR deleting file: ${err.message}`;
        }
    }
    async terminalRun(command) {
        return new Promise((resolve) => {
            let output = "";
            if (!this._terminal) {
                const pty = {
                    onDidWrite: this._terminalWriteEmitter.event,
                    open: () => { },
                    close: () => { this._terminal = undefined; },
                    handleInput: (data) => {
                        // Future: handle user input to process
                        this._terminalWriteEmitter.fire(data);
                    }
                };
                this._terminal = vscode.window.createTerminal({
                    name: "Ashborn Terminal",
                    pty
                });
            }
            this._terminal.show(true);
            this._terminalWriteEmitter.fire(`\r\n\x1b[35m$ ${command}\x1b[0m\r\n`);
            const cp = require("child_process");
            const wsRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
            const child = cp.spawn(command, {
                shell: true,
                cwd: wsRoot
            });
            child.stdout.on("data", (data) => {
                const str = data.toString();
                output += str;
                // Convert LF to CRLF for terminal display
                this._terminalWriteEmitter.fire(str.replace(/\n/g, "\r\n"));
            });
            child.stderr.on("data", (data) => {
                const str = data.toString();
                output += str;
                this._terminalWriteEmitter.fire(`\x1b[31m${str.replace(/\n/g, "\r\n")}\x1b[0m`);
            });
            child.on("close", (code) => {
                this._terminalWriteEmitter.fire(`\r\n\x1b[32m[Process exited with code ${code}]\x1b[0m\r\n`);
                resolve(output || (code === 0 ? "Command executed successfully." : `Command failed with code ${code}`));
            });
            child.on("error", (err) => {
                this._terminalWriteEmitter.fire(`\r\n\x1b[31m[Error: ${err.message}]\x1b[0m\r\n`);
                resolve(`ERROR: ${err.message}`);
            });
        });
    }
}
exports.ActionExecutor = ActionExecutor;
//# sourceMappingURL=actionExecutor.js.map