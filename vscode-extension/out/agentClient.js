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
exports.AgentClient = void 0;
const http = __importStar(require("http"));
class AgentClient {
    constructor(port = 8765) {
        this._activeRequest = null;
        this._port = port;
    }
    set port(p) {
        this._port = p;
    }
    async healthCheck() {
        return new Promise((resolve) => {
            const req = http.get(`http://127.0.0.1:${this._port}/health`, (res) => {
                let data = "";
                res.on("data", (c) => (data += c));
                res.on("end", () => resolve(res.statusCode === 200));
            });
            req.on("error", () => resolve(false));
            req.setTimeout(2000, () => {
                req.destroy();
                resolve(false);
            });
        });
    }
    abort() {
        if (this._activeRequest) {
            this._activeRequest.destroy();
            this._activeRequest = null;
        }
    }
    async sendMessage(task, sessionId, mode, onEvent) {
        return new Promise((resolve, reject) => {
            const body = JSON.stringify({ task, session_id: sessionId, mode });
            const options = {
                hostname: "127.0.0.1",
                port: this._port,
                path: "/chat/stream",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(body),
                    Accept: "text/event-stream",
                },
            };
            const req = http.request(options, (res) => {
                let buf = "";
                res.on("data", (chunk) => {
                    buf += chunk.toString();
                    const lines = buf.split("\n");
                    buf = lines.pop() ?? "";
                    for (const line of lines) {
                        if (!line.startsWith("data:"))
                            continue;
                        const raw = line.slice(5).trim();
                        if (!raw)
                            continue;
                        try {
                            const evt = JSON.parse(raw);
                            onEvent(evt);
                            if (evt.type === "done" || evt.type === "error") {
                                resolve();
                            }
                        }
                        catch {
                            /* ignore malformed frames */
                        }
                    }
                });
                res.on("end", resolve);
                res.on("error", reject);
            });
            req.on("error", reject);
            req.write(body);
            req.end();
            this._activeRequest = req;
        });
    }
    async sendToolResult(callId, result) {
        return new Promise((resolve, reject) => {
            const body = JSON.stringify({ call_id: callId, result });
            const req = http.request({
                hostname: "127.0.0.1",
                port: this._port,
                path: "/tool/result",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(body),
                },
            }, (res) => {
                res.resume();
                res.on("end", resolve);
            });
            req.on("error", reject);
            req.write(body);
            req.end();
        });
    }
    async reset() {
        return new Promise((resolve, reject) => {
            const req = http.request({
                hostname: "127.0.0.1",
                port: this._port,
                path: "/reset",
                method: "POST",
                headers: { "Content-Length": 0 },
            }, (res) => {
                res.resume();
                res.on("end", resolve);
            });
            req.on("error", reject);
            req.end();
        });
    }
    async getConfig() {
        return new Promise((resolve, reject) => {
            const req = http.request({
                hostname: "127.0.0.1",
                port: this._port,
                path: "/config",
                method: "GET",
            }, (res) => {
                let data = "";
                res.on("data", (c) => (data += c));
                res.on("end", () => resolve(JSON.parse(data)));
            });
            req.on("error", reject);
            req.end();
        });
    }
    async updateConfig(settings) {
        return new Promise((resolve, reject) => {
            const body = JSON.stringify({ settings });
            const req = http.request({
                hostname: "127.0.0.1",
                port: this._port,
                path: "/config",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(body),
                },
            }, (res) => {
                let data = "";
                res.on("data", (c) => (data += c));
                res.on("end", () => resolve(JSON.parse(data)));
            });
            req.on("error", reject);
            req.write(body);
            req.end();
        });
    }
    async getCompletion(filePath, contentBefore, contentAfter) {
        return new Promise((resolve, reject) => {
            const body = JSON.stringify({
                file_path: filePath,
                content_before: contentBefore,
                content_after: contentAfter,
            });
            const req = http.request({
                hostname: "127.0.0.1",
                port: this._port,
                path: "/completion",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(body),
                },
            }, (res) => {
                let data = "";
                res.on("data", (c) => (data += c));
                res.on("end", () => {
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.status === "ok") {
                            resolve(parsed.completion || "");
                        }
                        else {
                            resolve("");
                        }
                    }
                    catch {
                        resolve("");
                    }
                });
            });
            req.on("error", () => resolve(""));
            req.write(body);
            req.end();
        });
    }
    async executeCodeAction(action, filePath, selectedText, fullText) {
        return new Promise((resolve, reject) => {
            const body = JSON.stringify({
                action,
                file_path: filePath,
                selected_text: selectedText,
                full_text: fullText,
            });
            const req = http.request({
                hostname: "127.0.0.1",
                port: this._port,
                path: "/code_action",
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(body),
                },
            }, (res) => {
                let data = "";
                res.on("data", (c) => (data += c));
                res.on("end", () => {
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.status === "ok") {
                            resolve(parsed.result || "");
                        }
                        else {
                            resolve("");
                        }
                    }
                    catch {
                        resolve("");
                    }
                });
            });
            req.on("error", () => resolve(""));
            req.write(body);
            req.end();
        });
    }
}
exports.AgentClient = AgentClient;
//# sourceMappingURL=agentClient.js.map