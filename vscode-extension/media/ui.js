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
  const modeEl   = document.getElementById("mode-select");
  const dotEl    = document.getElementById("status-dot");
  const txtEl    = document.getElementById("status-text");

  // ── State ───────────────────────────────────────────────────────────────────
  let currentBubble = null;   // <div> being streamed into
  let currentText   = "";     // raw text accumulated
  let cursorEl      = null;   // blinking cursor span
  let isStreaming   = false;

  // ── Simple Markdown renderer (no external deps) ──────────────────────────────
  function renderMarkdown(text) {
    // Code blocks
    text = text.replace(/```([\w]*)?\n([\s\S]*?)```/g, (_, lang, code) => {
      const escaped = escapeHtml(code.trimEnd());
      return `<pre><code class="lang-${lang || "text"}">${escaped}</code></pre>`;
    });
    // Inline code
    text = text.replace(/`([^`]+)`/g, (_, c) => `<code>${escapeHtml(c)}</code>`);
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic
    text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
    // Headers
    text = text.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    text = text.replace(/^## (.+)$/gm,  "<h2>$1</h2>");
    text = text.replace(/^# (.+)$/gm,   "<h1>$1</h1>");
    // Horizontal rule
    text = text.replace(/^---+$/gm, "<hr/>");
    // Unordered list items
    text = text.replace(/^[•\-\*] (.+)$/gm, "<li>$1</li>");
    // Numbered list
    text = text.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
    // Checkboxes
    text = text.replace(/✓ (.+)/g, '<span style="color:#4caf82">✓ $1</span>');
    text = text.replace(/✗ (.+)/g, '<span style="color:#e05560">✗ $1</span>');
    // Line breaks for non-HTML lines
    text = text.replace(/\n/g, "<br/>");
    return text;
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── UI helpers ───────────────────────────────────────────────────────────────
  function setStatus(state, label) {
    dotEl.className = `status-dot ${state}`;
    txtEl.textContent = label;
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

  function startAgentMessage() {
    removeWelcome();
    const msg = document.createElement("div");
    msg.className = "msg msg-agent";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    // Blinking cursor
    cursorEl = document.createElement("span");
    cursorEl.className = "cursor";
    bubble.appendChild(cursorEl);

    msg.innerHTML = `<div class="msg-label">🔥 Ashborn</div>`;
    msg.appendChild(bubble);
    chat.appendChild(msg);
    currentBubble = bubble;
    currentText   = "";
    scrollBottom();
    return bubble;
  }

  function appendChunk(text) {
    if (!currentBubble) startAgentMessage();
    currentText += text;
    if (cursorEl) cursorEl.remove();
    currentBubble.innerHTML = renderMarkdown(currentText);
    // Re-append cursor
    cursorEl = document.createElement("span");
    cursorEl.className = "cursor";
    currentBubble.appendChild(cursorEl);
    scrollBottom();
  }

  function finalizeMessage() {
    if (currentBubble) {
      if (cursorEl) cursorEl.remove();
      currentBubble.innerHTML = renderMarkdown(currentText);
      currentBubble = null;
      currentText   = "";
      cursorEl      = null;
    }
    scrollBottom();
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
    modeEl.disabled   = !enabled;
    btnStop.disabled  = enabled;
  }

  // ── Send message ─────────────────────────────────────────────────────────────
  function sendMessage() {
    const task = input.value.trim();
    if (!task || isStreaming) return;
    input.value = "";
    setInputEnabled(false);
    setStatus("thinking", "Thinking…");
    vscode.postMessage({ type: "send", task, mode: modeEl.value });
  }

  // ── Button handlers ───────────────────────────────────────────────────────────
  btnSend.addEventListener("click", sendMessage);

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
          setStatus("thinking", msg.content ?? "Thinking…");
          if (!currentBubble) startAgentMessage();
        } else if (msg.state === "executing") {
          setStatus("executing", msg.content ?? "Executing…");
          addStatusMsg(msg.content ?? "Executing…");
        } else if (msg.state === "idle") {
          setStatus("idle", msg.content ?? "Idle");
          removeStatusMsgs();
        } else if (msg.state === "error") {
          setStatus("error", "Error");
        }
        break;

      case "chunk":
        appendChunk(msg.content ?? "");
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
    }
  });

  // Initial state
  setInputEnabled(true);
  btnStop.disabled = true;
})();
