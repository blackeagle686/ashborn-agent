// ui.js — Ashborn Agent WebView client script
// Runs inside the VS Code WebView (browser context, NOT Node.js)
// Communicates with extension host via acquireVsCodeApi()

(function () {
  "use strict";

  const vscode = acquireVsCodeApi();

  // ── DOM refs ────────────────────────────────────────────────────────────────
  const chat     = document.getElementById("chat-container");
  const input    = document.getElementById("input");
  const btnSend  = document.getElementById("btn-send");
  const btnRun   = document.getElementById("btn-run");
  const btnStop  = document.getElementById("btn-stop");
  const btnReset = document.getElementById("btn-reset");
  const modePills = document.querySelectorAll(".mode-pill");
  const dotEl    = document.getElementById("status-dot");
  const txtEl    = document.getElementById("status-text");
  
  const settingsPanel = document.getElementById("settings-panel");
  const btnSettings   = document.getElementById("btn-settings");
  const btnTheme      = document.getElementById("btn-theme");
  const btnCloseSettings = document.getElementById("btn-close-settings");
  const btnSaveSettings  = document.getElementById("btn-save-settings");
  const settingsStatus   = document.getElementById("settings-status");
  
  const cfgApiKey   = document.getElementById("cfg-api-key");
  const cfgBaseUrl  = document.getElementById("cfg-base-url");
  const cfgModel    = document.getElementById("cfg-model");
  const cfgLogLevel = document.getElementById("cfg-log-level");
  
  const contextPanel = document.getElementById("context-panel");
  const btnContext    = document.getElementById("btn-context");
  const btnCloseContext = document.getElementById("btn-close-context");
  const contextDataEl   = document.getElementById("context-data");

  // ── Voice / TTS refs ──────────────────────────────────────────────────────────
  const btnMic          = document.getElementById("btn-mic");
  const listeningOverlay = document.getElementById("listening-overlay");
  const listeningTranscript = document.getElementById("listening-transcript");
  const btnStopMic      = document.getElementById("btn-stop-mic");
  const ttsPlayer       = document.getElementById("tts-player");
  let recognition = null;

  // ── State ───────────────────────────────────────────────────────────────────
  let currentBubble = null;   // <div> being streamed into
  let currentText   = "";     // raw text accumulated
  let cursorEl      = null;   // blinking cursor span
  let isStreaming   = false;
  let currentMode   = "auto";

  // ── Splash Screen: Poll backend until ready ──────────────────────────────────
  const splashScreen = document.getElementById("splash-screen");
  const splashStatusText = document.getElementById("splash-status-text");

  const SPLASH_MESSAGES = [
    "Connecting to backend…",
    "Loading AI modules…",
    "Initializing Phoenix framework…",
    "Warming up the agent…",
    "Almost ready…",
  ];
  let splashMsgIndex = 0;

  function dismissSplash() {
    splashScreen.classList.add("splash-exit");
    splashScreen.addEventListener("transitionend", () => {
      splashScreen.style.display = "none";
    }, { once: true });
  }

  async function pollBackend() {
    try {
      const res = await fetch("http://127.0.0.1:8765/health", { signal: AbortSignal.timeout(3000) });
      const data = await res.json();
      if (data.agent_ready === true) {
        splashStatusText.textContent = "✅ Agent ready!";
        setTimeout(dismissSplash, 700);
        return; // Done — stop polling
      }
      splashStatusText.textContent = "Server up, loading agent…";
    } catch (_) {
      // Cycle through loading messages while waiting
      splashMsgIndex = (splashMsgIndex + 1) % SPLASH_MESSAGES.length;
      splashStatusText.textContent = SPLASH_MESSAGES[splashMsgIndex];
    }
    setTimeout(pollBackend, 2000);
  }

  // Start polling immediately
  setTimeout(pollBackend, 500);


  // ── Optimized Markdown renderer ──────────────────────────────────────────────
  const mdRegexes = [
    [/```([\w]*)?\n([\s\S]*?)```/g, (_, lang, code) => `<pre><code class="lang-${lang || "text"}">${escapeHtml(code.trimEnd())}</code></pre>`],
    [/`([^`]+)`/g, (_, c) => `<code>${escapeHtml(c)}</code>`],
    [/\*\*(.+?)\*\*/g, "<strong>$1</strong>"],
    [/\*(.+?)\*/g, "<em>$1</em>"],
    [/^### (.+)$/gm, "<h3>$1</h3>"],
    [/^## (.+)$/gm,  "<h2>$1</h2>"],
    [/^# (.+)$/gm,   "<h1>$1</h1>"],
    [/^---+$/gm, "<hr/>"],
    [/^[•\-\*] (.+)$/gm, "<li>$1</li>"],
    [/^\d+\. (.+)$/gm, "<li>$1</li>"],
    [/✓ (.+)/g, '<span style="color:#4caf82">✓ $1</span>'],
    [/✗ (.+)/g, '<span style="color:#e05560">✗ $1</span>'],
    [/\n/g, "<br/>"]
  ];

  // File-path regex: matches paths like ashborn/server.py or ./tools/file.ts
  const FILE_PATH_RE = /(?<![`"'])([\w./][\w./\-]*\.(?:py|js|ts|tsx|jsx|json|yaml|yml|toml|md|sh|env|txt|css|html|go|rs|java|c|cpp|h|sql|cfg|ini))(?![`"'])/g;

  function linkifyFilePaths(html) {
    // Don't linkify inside <pre> or <code> blocks — preserve those as-is
    return html.replace(FILE_PATH_RE, (match) => {
      return `<span class="file-link" data-path="${match}" title="Click to open ${match}">${match}</span>`;
    });
  }

  function renderMarkdown(text) {
    let html = text;
    for (const [reg, repl] of mdRegexes) {
      html = html.replace(reg, repl);
    }
    html = linkifyFilePaths(html);
    return html;
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── UI helpers ───────────────────────────────────────────────────────────────
  function setStatus(state, label, role = null) {
    dotEl.className = `status-dot ${state}`;
    txtEl.textContent = label;
    updateAgentHUD(role);
  }

  function updateAgentHUD(role) {
    const units = document.querySelectorAll(".agent-unit");
    units.forEach(u => {
      if (u.dataset.role === role) {
        u.classList.add("active");
      } else {
        u.classList.remove("active");
      }
    });
  }

  function scrollBottom() {
    chat.scrollTop = chat.scrollHeight;
  }

  function removeWelcome() {
    const w = chat.querySelector(".welcome");
    if (w) w.remove();
  }

  function addUserMessage(text) {
    removeWelcome();
    const msg = document.createElement("div");
    msg.className = "msg msg-user";
    msg.innerHTML = `
      <div class="msg-label">You</div>
      <div class="msg-bubble">${escapeHtml(text)}</div>
    `;
    chat.appendChild(msg);
    scrollBottom();
  }

  function startAgentMessage(role = null) {
    removeWelcome();
    const msg = document.createElement("div");
    msg.className = "msg msg-agent";
    if (role) msg.setAttribute("data-role", role);

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble streaming";

    const label = role ? role.charAt(0).toUpperCase() + role.slice(1) : "Ashborn";
    msg.innerHTML = `<div class="msg-label">🔥 ${label}</div>`;
    msg.appendChild(bubble);
    chat.appendChild(msg);
    currentBubble = bubble;
    currentText   = "";
    scrollBottom();
    return bubble;
  }

  function appendChunk(text, role = null) {
    if (!currentBubble) startAgentMessage(role);
    currentText += text;
    
    // Efficiently update HTML
    currentBubble.innerHTML = renderMarkdown(currentText);
    
    // Only scroll if we are near bottom
    const threshold = 100;
    const isNearBottom = (chat.scrollHeight - chat.scrollTop - chat.clientHeight) < threshold;
    if (isNearBottom) {
      scrollBottom();
    }
  }

  function finalizeMessage() {
    if (currentBubble) {
      currentBubble.classList.remove("streaming");
      currentBubble.innerHTML = renderMarkdown(currentText);
      
      // Add reply + play buttons
      const msgEl = currentBubble.parentElement;
      const actionsRow = document.createElement("div");
      actionsRow.className = "msg-actions";

      const replyBtn = document.createElement("button");
      replyBtn.className = "btn-reply";
      replyBtn.textContent = "↩ Reply";
      const capturedText = currentText;
      replyBtn.addEventListener("click", () => {
        const quoted = capturedText.replace(/\n/g, " ").substring(0, 120);
        input.value = `> ${quoted}\n`;
        input.focus();
        input.dispatchEvent(new Event("input"));
      });

      const ICON_PLAY = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M11.536 14.01A8.47 8.47 0 0 0 14.026 8a8.47 8.47 0 0 0-2.49-6.01l-.708.707A7.48 7.48 0 0 1 13.025 8c0 2.071-.84 3.946-2.197 5.303l.708.707z"/><path d="M10.121 12.596A6.48 6.48 0 0 0 12.025 8a6.48 6.48 0 0 0-1.904-4.596l-.707.707A5.48 5.48 0 0 1 11.025 8a5.48 5.48 0 0 1-1.61 3.89l.706.706z"/><path d="M10.025 8a4.49 4.49 0 0 1-1.318 3.182L8 10.475A3.5 3.5 0 0 0 9.025 8c0-.966-.392-1.841-1.025-2.475l.707-.707A4.49 4.49 0 0 1 10.025 8M7 4a.5.5 0 0 0-.812-.39L3.825 5.5H1.5A.5.5 0 0 0 1 6v4a.5.5 0 0 0 .5.5h2.325l2.363 1.89A.5.5 0 0 0 7 12V4z"/></svg>`;

      const playBtn = document.createElement("button");
      playBtn.className = "btn-tts";
      playBtn.title = "Read aloud";
      playBtn.innerHTML = ICON_PLAY;
      playBtn.addEventListener("click", () => playTTS(capturedText, playBtn));

      actionsRow.appendChild(replyBtn);
      actionsRow.appendChild(playBtn);
      msgEl.appendChild(actionsRow);

      currentBubble = null;
      currentText   = "";
    }
    scrollBottom();
  }

  // ── Text-to-Speech ─────────────────────────────────────────────────────────
  async function playTTS(text, btn) {
    // Strip markdown formatting for clean speech
    const clean = text
      .replace(/```[\s\S]*?```/g, "code block.")
      .replace(/`[^`]+`/g, "")
      .replace(/[*_#>]/g, "")
      .replace(/<[^>]+>/g, "")
      .trim();

    const ICON_PLAY = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M11.536 14.01A8.47 8.47 0 0 0 14.026 8a8.47 8.47 0 0 0-2.49-6.01l-.708.707A7.48 7.48 0 0 1 13.025 8c0 2.071-.84 3.946-2.197 5.303l.708.707z"/><path d="M10.121 12.596A6.48 6.48 0 0 0 12.025 8a6.48 6.48 0 0 0-1.904-4.596l-.707.707A5.48 5.48 0 0 1 11.025 8a5.48 5.48 0 0 1-1.61 3.89l.706.706z"/><path d="M10.025 8a4.49 4.49 0 0 1-1.318 3.182L8 10.475A3.5 3.5 0 0 0 9.025 8c0-.966-.392-1.841-1.025-2.475l.707-.707A4.49 4.49 0 0 1 10.025 8M7 4a.5.5 0 0 0-.812-.39L3.825 5.5H1.5A.5.5 0 0 0 1 6v4a.5.5 0 0 0 .5.5h2.325l2.363 1.89A.5.5 0 0 0 7 12V4z"/></svg>`;
    const ICON_LOAD = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M2 1.5a.5.5 0 0 1 .5-.5h11a.5.5 0 0 1 0 1h-1v1a4.5 4.5 0 0 1-2.557 4.06c-.29.139-.443.377-.443.59v.7c0 .213.154.451.443.59A4.5 4.5 0 0 1 12.5 13v1h1a.5.5 0 0 1 0 1h-11a.5.5 0 1 1 0-1h1v-1a4.5 4.5 0 0 1 2.557-4.06c.29-.139.443-.377.443-.59v-.7c0-.213-.154-.451-.443-.59A4.5 4.5 0 0 1 3.5 3V2h-1a.5.5 0 0 1-.5-.5zm2.5.5v1a3.5 3.5 0 0 0 1.989 3.158c.533.256 1.011.791 1.011 1.491v.702c0 .7-.478 1.235-1.011 1.491A3.5 3.5 0 0 0 4.5 13v1h7v-1a3.5 3.5 0 0 0-1.989-3.158C8.978 9.586 8.5 9.052 8.5 8.351v-.702c0-.7.478-1.235 1.011-1.491A3.5 3.5 0 0 0 11.5 3V2h-7z"/></svg>`;
    const ICON_STOP = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5 3.5h6A1.5 1.5 0 0 1 12.5 5v6a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 11V5A1.5 1.5 0 0 1 5 3.5z"/></svg>`;

    if (!clean) return;
    const prevHTML = btn ? btn.innerHTML : "";
    if (btn) { btn.innerHTML = ICON_LOAD; btn.disabled = true; }

    try {
      const res = await fetch("http://127.0.0.1:8765/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean })
      });
      const data = await res.json();
      if (data.status === "ok") {
        const audioSrc = "data:audio/mp3;base64," + data.audio;
        ttsPlayer.src = audioSrc;
        ttsPlayer.play();
        if (btn) { btn.innerHTML = ICON_STOP; btn.disabled = false; }
        ttsPlayer.onended = () => { if (btn) { btn.innerHTML = ICON_PLAY; } };
        // Clicking again stops
        if (btn) btn.onclick = () => { ttsPlayer.pause(); ttsPlayer.currentTime = 0; btn.innerHTML = ICON_PLAY; btn.onclick = () => playTTS(text, btn); };
      }
    } catch (e) {
      if (btn) { btn.innerHTML = prevHTML; btn.disabled = false; }
    }
  }

  function addStatusMsg(content) {
    removeWelcome();
    // Remove previous status msgs to avoid clutter
    const prev = chat.querySelector(".status-msg");
    if (prev) prev.remove();

    const el = document.createElement("div");
    el.className = "status-msg";
    el.innerHTML = `<span class="spin">⟳</span> ${escapeHtml(content)}`;
    chat.appendChild(el);
    scrollBottom();
  }

  function removeStatusMsgs() {
    chat.querySelectorAll(".status-msg").forEach((e) => e.remove());
  }

  function addErrorMsg(content) {
    removeStatusMsgs();
    const el = document.createElement("div");
    el.className = "msg msg-agent";
    el.innerHTML = `
      <div class="msg-label" style="color:#e05560">⚠ Error</div>
      <div class="msg-bubble" style="border-color:#3a2020;background:#1a1010">${escapeHtml(content)}</div>
    `;
    chat.appendChild(el);
    scrollBottom();
  }

  function setInputEnabled(enabled) {
    isStreaming = !enabled;
    input.disabled    = !enabled;
    btnSend.disabled  = !enabled;
    btnRun.disabled   = !enabled;
    modePills.forEach(p => p.disabled = !enabled);
    btnStop.disabled  = enabled;
  }

  // ── Send message ─────────────────────────────────────────────────────────────
  function sendMessage() {
    const task = input.value.trim();
    if (!task || isStreaming) return;
    input.value = "";
    setInputEnabled(false);
    setStatus("thinking", "Thinking…");
    vscode.postMessage({ type: "send", task, mode: currentMode });
  }

  // ── File-link click handler (delegated) ──────────────────────────────────────
  chat.addEventListener("click", (e) => {
    const link = e.target.closest(".file-link");
    if (link) {
      const p = link.dataset.path;
      // Try absolute first, then workspace-relative
      const workspaceRoot = typeof WORKSPACE_ROOT !== "undefined" ? WORKSPACE_ROOT : "";
      const fullPath = p.startsWith("/") ? p : (workspaceRoot ? workspaceRoot + "/" + p : p);
      vscode.postMessage({ type: "openFile", path: fullPath });
    }
  });

  // ── Button handlers ───────────────────────────────────────────────────────────
  btnSend.addEventListener("click", sendMessage);

  // Topbar Toggle
  const topbar = document.getElementById("topbar");
  const topbarHeader = document.getElementById("topbar-header");
  topbarHeader.addEventListener("click", () => {
    topbar.classList.toggle("collapsed");
    const isCollapsed = topbar.classList.contains("collapsed");
    document.getElementById("btn-toggle-topbar").title = isCollapsed ? "Expand Controls" : "Collapse Controls";
  });

  // Mode Pill Handlers
  modePills.forEach(pill => {
    pill.addEventListener("click", () => {
      if (isStreaming) return;
      modePills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentMode = pill.dataset.mode;
    });
  });

  btnRun.addEventListener("click", () => {
    const task = input.value.trim();
    if (!task || isStreaming) return;
    input.value = "";
    setInputEnabled(false);
    setStatus("thinking", "Thinking…");
    vscode.postMessage({ type: "send", task, mode: "plan" });
  });

  btnStop.addEventListener("click", () => {
    vscode.postMessage({ type: "stop" });
    setStatus("idle", "Stopped.");
    setInputEnabled(true);
    finalizeMessage();
    removeStatusMsgs();
  });

  btnReset.addEventListener("click", () => {
    vscode.postMessage({ type: "reset" });
    setStatus("idle", "Idle");
    setInputEnabled(true);
    finalizeMessage();
    removeStatusMsgs();
    chat.innerHTML = `
      <div class="welcome">
        <div class="welcome-icon">🔥</div>
        <div class="welcome-title">Ashborn Agent</div>
        <div class="welcome-sub">Session reset. Ready for a new task.</div>
      </div>`;
  });

  if (btnTheme) {
    btnTheme.addEventListener("click", () => {
      // Let the extension host toggle the global theme. 
      // VS Code will automatically update document.body.classList.
      const isLight = document.body.classList.contains("vscode-light");
      vscode.postMessage({ type: "theme", isLight: !isLight });
    });
  }

  btnSettings.addEventListener("click", () => {
    settingsPanel.style.display = "flex";
    settingsStatus.textContent = "Loading configuration...";
    settingsStatus.className = "settings-status";
    vscode.postMessage({ type: "getConfig" });
  });

  btnCloseSettings.addEventListener("click", () => {
    settingsPanel.style.display = "none";
  });

  btnContext.addEventListener("click", () => {
    const isHidden = contextPanel.style.display === "none";
    contextPanel.style.display = isHidden ? "flex" : "none";
    if (isHidden) {
      vscode.postMessage({ type: "getContext" });
    }
  });

  btnCloseContext.addEventListener("click", () => {
    contextPanel.style.display = "none";
  });

  btnSaveSettings.addEventListener("click", () => {
    const settings = {
      OPENAI_API_KEY: cfgApiKey.value,
      OPENAI_BASE_URL: cfgBaseUrl.value,
      OPENAI_LLM_MODEL: cfgModel.value,
      LOG_LEVEL: cfgLogLevel.value
    };
    settingsStatus.textContent = "Saving...";
    settingsStatus.className = "settings-status";
    vscode.postMessage({ type: "saveConfig", settings });
  });

  // ── Mention List logic ──────────────────────────────────────────────────────
  const mentionList = document.getElementById("mention-list");
  let allFiles = [];
  let filteredFiles = [];
  let selectedIndex = 0;
  let mentionStartIdx = -1;

  function showMentionList(show) {
    mentionList.style.display = show ? "block" : "none";
    if (!show) {
      selectedIndex = 0;
      filteredFiles = [];
    }
  }

  function renderMentionList() {
    mentionList.innerHTML = "";
    filteredFiles.forEach((file, i) => {
      const item = document.createElement("div");
      item.className = "mention-item" + (i === selectedIndex ? " selected" : "");
      const icon = file.endsWith("/") ? "📁" : "📄";
      item.innerHTML = `<span class="mention-icon">${icon}</span><span class="mention-path">${file}</span>`;
      item.onclick = () => selectMention(file);
      mentionList.appendChild(item);
    });
    if (filteredFiles.length > 0) {
      const selectedItem = mentionList.children[selectedIndex];
      if (selectedItem) selectedItem.scrollIntoView({ block: "nearest" });
    }
  }

  function selectMention(file) {
    const text = input.value;
    const before = text.substring(0, mentionStartIdx);
    const after = text.substring(input.selectionStart);
    input.value = before + "@" + file + " " + after;
    showMentionList(false);
    input.focus();
    // trigger auto-resize
    input.dispatchEvent(new Event('input'));
  }

  input.addEventListener("input", (e) => {
    // Auto-resize
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";

    // Mention detection
    const text = input.value;
    const cursor = input.selectionStart;
    const lastAt = text.lastIndexOf("@", cursor - 1);

    if (lastAt !== -1) {
      const query = text.substring(lastAt + 1, cursor);
      // Only trigger if @ is at start or after space
      if (lastAt === 0 || /\s/.test(text[lastAt - 1])) {
        if (!query.includes(" ")) {
          mentionStartIdx = lastAt;
          if (allFiles.length === 0) {
            vscode.postMessage({ type: "getFiles" });
          }
          filteredFiles = allFiles.filter(f => f.toLowerCase().includes(query.toLowerCase())).slice(0, 10);
          if (filteredFiles.length > 0) {
            selectedIndex = 0;
            showMentionList(true);
            renderMentionList();
            return;
          }
        }
      }
    }
    showMentionList(false);
  });

  input.addEventListener("keydown", (e) => {
    if (mentionList.style.display === "block") {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % filteredFiles.length;
        renderMentionList();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + filteredFiles.length) % filteredFiles.length;
        renderMentionList();
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        selectMention(filteredFiles[selectedIndex]);
      } else if (e.key === "Escape") {
        showMentionList(false);
      }
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // ── Messages FROM extension host ──────────────────────────────────────────────
  window.addEventListener("message", (event) => {
    const msg = event.data;

    switch (msg.type) {
      case "user_message":
        addUserMessage(msg.content);
        break;

      case "status":
        if (msg.state === "thinking") {
          setStatus("thinking", msg.content ?? "Thinking…", msg.role);
          if (!currentBubble) startAgentMessage(msg.role);
        } else if (msg.state === "executing") {
          setStatus("executing", msg.content ?? "Executing…", msg.role);
          addStatusMsg(msg.content ?? "Executing…");
        } else if (msg.state === "idle") {
          setStatus("idle", msg.content ?? "Idle", null);
          removeStatusMsgs();
        } else if (msg.state === "error") {
          setStatus("error", "Error", null);
        }
        break;

      case "chunk":
        appendChunk(msg.content ?? "", msg.role);
        break;

      case "done":
        finalizeMessage();
        removeStatusMsgs();
        setStatus("idle", "Done ✓");
        setInputEnabled(true);
        break;

      case "error":
        finalizeMessage();
        removeStatusMsgs();
        addErrorMsg(msg.content ?? "Unknown error");
        setStatus("error", "Error");
        setInputEnabled(true);
        break;

      case "files":
        allFiles = msg.files || [];
        // Trigger a re-filter if already typing
        input.dispatchEvent(new Event('input'));
        break;

      case "reset":
        // handled by button
        break;

      case "config":
        cfgApiKey.value = msg.config.OPENAI_API_KEY || "";
        cfgBaseUrl.value = msg.config.OPENAI_BASE_URL || "";
        cfgModel.value = msg.config.OPENAI_LLM_MODEL || "gpt-4o";
        cfgLogLevel.value = msg.config.ASHBORN_LOG_LEVEL || "WARNING";
        settingsStatus.textContent = "";
        break;

      case "configSaved":
        if (msg.success) {
          settingsStatus.textContent = "✓ Saved and Agent reloaded!";
          settingsStatus.className = "settings-status success";
          setTimeout(() => { settingsPanel.style.display = "none"; }, 1500);
        } else {
          settingsStatus.textContent = "✗ Failed: " + msg.message;
          settingsStatus.className = "settings-status error";
        }
        break;

      case "context":
        contextDataEl.textContent = msg.content || "No context data available.";
        break;
    }
  });

  // ── Speech-to-Text (Backend Implementation) ────────────────────────────────
  let isRecording = false;

  async function startListening() {
    listeningTranscript.textContent = "Recording... (Speak now)";
    listeningTranscript.style.color = "";
    listeningOverlay.style.display = "flex";
    btnStopMic.textContent = "Done / Stop";
    isRecording = true;

    try {
      const res = await fetch("http://127.0.0.1:8765/stt/start", { method: "POST" });
      const data = await res.json();
      if (data.status !== "ok") {
        throw new Error(data.message || "Failed to start recording");
      }
    } catch (e) {
      listeningTranscript.textContent = "❌ Error: " + e.message;
      listeningTranscript.style.color = "#ff4444";
      btnStopMic.textContent = "Close";
      isRecording = false;
    }
  }

  async function stopListening() {
    if (!isRecording) {
      listeningOverlay.style.display = "none";
      return;
    }
    isRecording = false;
    
    listeningTranscript.textContent = "Processing audio... ⏳";
    btnStopMic.textContent = "Please wait...";
    btnStopMic.disabled = true;

    try {
      const res = await fetch("http://127.0.0.1:8765/stt/stop", { method: "POST" });
      const data = await res.json();
      
      btnStopMic.disabled = false;
      
      if (data.status === "ok" && data.text) {
        input.value = data.text;
        input.dispatchEvent(new Event("input"));
        
        // Display the text for visual confirmation
        listeningTranscript.textContent = "✅ " + data.text;
        listeningTranscript.style.color = "#4caf82";
        btnStopMic.textContent = "Sending...";
        
        setTimeout(() => {
          listeningOverlay.style.display = "none";
          listeningTranscript.style.color = "";
          btnStopMic.textContent = "✕ Cancel";
          sendMessage();
        }, 2000);
      } else {
        throw new Error(data.message || "Could not transcribe audio");
      }
    } catch (e) {
      btnStopMic.disabled = false;
      listeningTranscript.textContent = "❌ Error: " + e.message;
      listeningTranscript.style.color = "#ff4444";
      btnStopMic.textContent = "Close";
    }
  }

  btnMic.addEventListener("click", startListening);
  btnStopMic.addEventListener("click", stopListening);

  // Initial state
  setInputEnabled(true);
  btnStop.disabled = true;
})();
