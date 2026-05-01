import * as http from "http";

export type AgentEvent = {
  type: "session" | "status" | "chunk" | "done" | "error";
  content?: string;
  session_id?: string;
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
}
