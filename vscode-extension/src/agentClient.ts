import * as http from "http";

export type AgentEvent = {
  type: "session" | "status" | "chunk" | "done" | "error" | "vscode_tool";
  content?: string;
  session_id?: string;
  tool?: string;
  arguments?: any;
  call_id?: string;
};

export class AgentClient {
  private _port: number;
  private _activeRequest: http.ClientRequest | null = null;

  constructor(port = 8765) {
    this._port = port;
  }

  set port(p: number) {
    this._port = p;
  }

  async healthCheck(): Promise<boolean> {
    return new Promise((resolve) => {
      const req = http.get(
        `http://127.0.0.1:${this._port}/health`,
        (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => resolve(res.statusCode === 200));
        }
      );
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

  async sendMessage(
    task: string,
    sessionId: string | undefined,
    mode: string,
    onEvent: (e: AgentEvent) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify({ task, session_id: sessionId, mode });

      const options: http.RequestOptions = {
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

        res.on("data", (chunk: Buffer) => {
          buf += chunk.toString();
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const raw = line.slice(5).trim();
            if (!raw) continue;
            try {
              const evt: AgentEvent = JSON.parse(raw);
              onEvent(evt);
              if (evt.type === "done" || evt.type === "error") {
                resolve();
              }
            } catch {
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

  async sendToolResult(callId: string, result: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify({ call_id: callId, result });
      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this._port,
          path: "/tool/result",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          res.resume();
          res.on("end", resolve);
        }
      );
      req.on("error", reject);
      req.write(body);
      req.end();
    });
  }

  async reset(): Promise<void> {
    return new Promise((resolve, reject) => {
      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this._port,
          path: "/reset",
          method: "POST",
          headers: { "Content-Length": 0 },
        },
        (res) => {
          res.resume();
          res.on("end", resolve);
        }
      );
      req.on("error", reject);
      req.end();
    });
  }

  async getConfig(): Promise<any> {
    return new Promise((resolve, reject) => {
      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this._port,
          path: "/config",
          method: "GET",
        },
        (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => resolve(JSON.parse(data)));
        }
      );
      req.on("error", reject);
      req.end();
    });
  }

  async updateConfig(settings: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify({ settings });
      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this._port,
          path: "/config",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => resolve(JSON.parse(data)));
        }
      );
      req.on("error", reject);
      req.write(body);
      req.end();
    });
  }

  async getCompletion(
    filePath: string,
    contentBefore: string,
    contentAfter: string
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify({
        file_path: filePath,
        content_before: contentBefore,
        content_after: contentAfter,
      });

      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this._port,
          path: "/completion",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => {
            try {
              const parsed = JSON.parse(data);
              if (parsed.status === "ok") {
                resolve(parsed.completion || "");
              } else {
                resolve("");
              }
            } catch {
              resolve("");
            }
          });
        }
      );
      req.on("error", () => resolve(""));
      req.write(body);
      req.end();
    });
  }

  async executeCodeAction(
    action: string,
    filePath: string,
    selectedText: string,
    fullText: string
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const body = JSON.stringify({
        action,
        file_path: filePath,
        selected_text: selectedText,
        full_text: fullText,
      });

      const req = http.request(
        {
          hostname: "127.0.0.1",
          port: this._port,
          path: "/code_action",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        },
        (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => {
            try {
              const parsed = JSON.parse(data);
              if (parsed.status === "ok") {
                resolve(parsed.result || "");
              } else {
                resolve("");
              }
            } catch {
              resolve("");
            }
          });
        }
      );
      req.on("error", () => resolve(""));
      req.write(body);
      req.end();
    });
  }
}
