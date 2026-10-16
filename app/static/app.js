const state = {
  token: localStorage.getItem("rag_token") || "",
  user: null,
  conversationId: null,
  docLimit: 20,
  docOffset: 0,
  docQuery: "",
  docTotal: 0,
  convLimit: 20,
  convOffset: 0,
  convQuery: "",
  convTotal: 0,
  streamAbort: null,
  streaming: false,
  answerBuffer: "",
  renderTimer: null,
  selectedDocuments: new Set(),
  selectedConversations: new Set(),
  currentDocumentIds: [],
  currentConversationIds: [],
};

function authHeaders(includeJson) {
  const headers = {};
  if (includeJson !== false) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) {
    headers.Authorization = "Bearer " + state.token;
  }
  return headers;
}

function setStatus(text, isError) {
  const element = document.getElementById("auth-status");
  if (!element) {
    return;
  }
  element.textContent = text;
  element.className = isError ? "status error" : "status";
}

function setDbStatus(text, status) {
  const element = document.getElementById("db-status");
  element.textContent = text;
  element.className = "badge " + (status || "");
}

function setProviderStatus(text, status) {
  const element = document.getElementById("provider-status");
  element.textContent = text;
  element.className = "badge " + (status || "");
}

function showToast(message, type) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast " + (type || "");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function () {
    toast.remove();
  }, 3200);
}

function setUser(user) {
  state.user = user;
  const loginScreen = document.getElementById("login-screen");
  const topbar = document.getElementById("topbar");
  const appLayout = document.getElementById("app-layout");
  const userInfo = document.getElementById("user-info");
  const logoutButton = document.getElementById("logout-btn");

  if (user) {
    loginScreen.classList.add("hidden");
    topbar.classList.remove("hidden");
    appLayout.classList.remove("hidden");
    userInfo.textContent = user.email + " · " + String(user.tenant_id).slice(0, 8);
    logoutButton.classList.remove("hidden");
  } else {
    loginScreen.classList.remove("hidden");
    topbar.classList.add("hidden");
    appLayout.classList.add("hidden");
    userInfo.textContent = "";
    logoutButton.classList.add("hidden");
  }
}

function switchAuthTab(mode) {
  const loginTab = document.getElementById("login-tab");
  const registerTab = document.getElementById("register-tab");
  const tenantField = document.getElementById("tenant-field");
  const loginButton = document.getElementById("login-btn");
  const registerButton = document.getElementById("register-btn");
  const isLogin = mode === "login";
  loginTab.className = isLogin ? "tab active" : "tab";
  registerTab.className = isLogin ? "tab" : "tab active";
  tenantField.className = isLogin ? "hidden" : "";
  loginButton.className = isLogin ? "" : "hidden";
  registerButton.className = isLogin ? "secondary hidden" : "secondary";
  setStatus("", false);
}

async function request(path, options) {
  const opts = options || {};
  const headers = Object.assign(authHeaders(opts.json !== false), opts.headers || {});
  const response = await fetch(path, Object.assign({}, opts, { headers }));
  if (response.status === 401) {
    state.token = "";
    localStorage.removeItem("rag_token");
    setUser(null);
  }
  if (!response.ok) {
    let detail = await response.text();
    try {
      const payload = JSON.parse(detail);
      detail = payload.detail || detail;
    } catch (error) {
      // 保留原始文本
    }
    throw new Error(detail || "请求失败：" + response.status);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderMarkdown(text) {
  try {
    if (window.marked && typeof window.marked.parse === "function") {
      const html = window.marked.parse(text);
      if (window.DOMPurify && typeof window.DOMPurify.sanitize === "function") {
        return window.DOMPurify.sanitize(html);
      }
    }
  } catch (error) {
    console.error("markdown render failed", error);
  }
  return escapeHtml(text).replace(/\n/g, "<br>");
}

async function checkDatabase() {
  try {
    await request("/api/v1/health/db", { json: false });
    setDbStatus("数据库已连接", "ok");
  } catch (error) {
    setDbStatus("数据库未连接", "error");
  }
}

async function checkProvider() {
  try {
    const data = await request("/api/v1/health", { json: false });
    const bothReady = data.embedding_configured && data.llm_configured;
    const anyReady = data.embedding_configured || data.llm_configured;
    setProviderStatus(
      "向量: " + data.embedding_provider + " / 模型: " + data.llm_provider,
      bothReady ? "ok" : (anyReady ? "warn" : "error")
    );
  } catch (error) {
    setProviderStatus("模型状态未知", "error");
  }
}

async function loadMe() {
  if (!state.token) {
    setUser(null);
    return;
  }
  try {
    const user = await request("/api/v1/auth/me");
    setUser(user);
  } catch (error) {
    setUser(null);
  }
}

async function register() {
  try {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const tenantName = document.getElementById("tenant-name").value.trim();
    await request("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: email,
        password: password,
        tenant_name: tenantName || null,
      }),
    });
    setStatus("注册成功，请登录", false);
    switchAuthTab("login");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function login() {
  try {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const data = await request("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email, password: password }),
    });
    state.token = data.access_token;
    localStorage.setItem("rag_token", state.token);
    setUser(data.user);
    setStatus("已登录：" + data.user.email, false);
    showToast("登录成功", "success");
    await loadDocuments();
    await loadConversations();
    await loadEvalRuns();
  } catch (error) {
    setStatus(error.message, true);
  }
}

function logout() {
  state.token = "";
  state.user = null;
  state.conversationId = null;
  localStorage.removeItem("rag_token");
  setUser(null);
  const chat = document.getElementById("chat-messages");
  if (chat) {
    chat.innerHTML = "";
  }
  showToast("已退出登录", "success");
}

async function loadDocuments(silent) {
  try {
    const params = new URLSearchParams();
    params.set("limit", String(state.docLimit));
    params.set("offset", String(state.docOffset));
    if (state.docQuery) {
      params.set("q", state.docQuery);
    }
    const page = await request("/api/v1/documents?" + params.toString());
    const list = document.getElementById("documents");
    list.innerHTML = "";
    const currentIds = [];

    page.items.forEach(function (doc) {
      currentIds.push(doc.id);
      const item = document.createElement("li");

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = state.selectedDocuments.has(doc.id);
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) {
          state.selectedDocuments.add(doc.id);
        } else {
          state.selectedDocuments.delete(doc.id);
        }
        updateDocSelectAll();
      });

      const name = document.createElement("span");
      const status = doc.status || "unknown";
      name.textContent = doc.filename + " (" + status + ")";
      if (status !== "ready" && status !== "failed") {
        name.className = "doc-pending";
      }

      const actions = document.createElement("div");
      actions.className = "doc-actions";

      const reingestButton = document.createElement("button");
      reingestButton.className = "mini secondary";
      reingestButton.textContent = "重新摄取";
      reingestButton.addEventListener("click", function () {
        reingestDocument(doc.id);
      });

      const deleteButton = document.createElement("button");
      deleteButton.className = "mini danger";
      deleteButton.textContent = "删除";
      deleteButton.addEventListener("click", function () {
        deleteDocument(doc.id);
      });

      actions.appendChild(reingestButton);
      actions.appendChild(deleteButton);
      item.appendChild(checkbox);
      item.appendChild(name);
      item.appendChild(actions);
      list.appendChild(item);
    });

    state.currentDocumentIds = currentIds;
    state.docTotal = page.total;
    const currentPage = Math.floor(state.docOffset / state.docLimit) + 1;
    const totalPages = Math.max(1, Math.ceil(page.total / state.docLimit));
    document.getElementById("doc-page-info").textContent =
      "第 " + currentPage + " / " + totalPages + " 页，共 " + page.total + " 个文档";
    document.getElementById("doc-prev-btn").disabled = state.docOffset <= 0;
    document.getElementById("doc-next-btn").disabled =
      state.docOffset + state.docLimit >= page.total;
    updateDocSelectAll();
  } catch (error) {
    if (!silent) {
      console.error(error);
    }
  }
}

function updateDocSelectAll() {
  const selectAll = document.getElementById("doc-select-all");
  const ids = state.currentDocumentIds;
  const selected = ids.filter(function (id) {
    return state.selectedDocuments.has(id);
  });
  selectAll.checked = ids.length > 0 && selected.length === ids.length;
  selectAll.indeterminate = selected.length > 0 && selected.length < ids.length;
}

function setDocumentCheckboxes(checked) {
  state.currentDocumentIds.forEach(function (id) {
    if (checked) {
      state.selectedDocuments.add(id);
    } else {
      state.selectedDocuments.delete(id);
    }
  });
  document.querySelectorAll("#documents input[type=checkbox]").forEach(function (checkbox) {
    checkbox.checked = checked;
  });
  updateDocSelectAll();
}

async function bulkDeleteDocuments() {
  const ids = Array.from(state.selectedDocuments);
  if (!ids.length) {
    showToast("请先选择要删除的文档", "error");
    return;
  }
  if (!confirm("确定批量删除选中的 " + ids.length + " 个文档吗？")) {
    return;
  }
  try {
    const result = await request("/api/v1/documents/bulk-delete", {
      method: "POST",
      body: JSON.stringify({ document_ids: ids }),
    });
    state.selectedDocuments.clear();
    showToast("已删除 " + result.count + " 个文档", "success");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function reingestAllDocuments() {
  if (!confirm("确定重新摄取所有文档吗？")) {
    return;
  }
  try {
    const result = await request("/api/v1/documents/reingest-all", { method: "POST" });
    showToast("已触发 " + result.count + " 个文档重新摄取", "success");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function uploadDocument() {
  const input = document.getElementById("file-input");
  if (!input.files.length) {
    showToast("请先选择文件", "error");
    return;
  }
  await sendDocument(input.files[0], false);
}

async function sendDocument(file, overwrite) {
  const form = new FormData();
  form.append("file", file);
  if (overwrite) {
    form.append("overwrite", "true");
  }
  const response = await fetch("/api/v1/documents", {
    method: "POST",
    headers: authHeaders(false),
    body: form,
  });
  if (response.status === 409 && !overwrite) {
    let detail = "同名文件已存在，是否覆盖原文件？";
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (error) {
      console.error(error);
    }
    if (confirm(detail)) {
      await sendDocument(file, true);
    }
    return;
  }
  if (!response.ok) {
    showToast(await response.text(), "error");
    return;
  }
  showToast(overwrite ? "已覆盖同名文件" : "上传成功，正在后台摄取", "success");
  state.docOffset = 0;
  await loadDocuments();
}

async function reingestDocument(documentId) {
  try {
    await request("/api/v1/documents/" + documentId + "/ingest", { method: "POST" });
    showToast("已触发重新摄取", "success");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteDocument(documentId) {
  if (!confirm("确定删除这个文档吗？")) {
    return;
  }
  try {
    await request("/api/v1/documents/" + documentId, { method: "DELETE" });
    showToast("文档已删除", "success");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadConversations() {
  try {
    const params = new URLSearchParams();
    params.set("limit", String(state.convLimit));
    params.set("offset", String(state.convOffset));
    if (state.convQuery) {
      params.set("q", state.convQuery);
    }
    const page = await request("/api/v1/chat/conversations?" + params.toString());
    const list = document.getElementById("conversations");
    list.innerHTML = "";
    const currentIds = [];

    page.items.forEach(function (conversation) {
      currentIds.push(conversation.id);
      const item = document.createElement("li");

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = state.selectedConversations.has(conversation.id);
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) {
          state.selectedConversations.add(conversation.id);
        } else {
          state.selectedConversations.delete(conversation.id);
        }
        updateConvSelectAll();
      });

      const info = document.createElement("div");
      info.className = "conversation-info";

      const button = document.createElement("button");
      button.className = "link-button";
      button.textContent = conversation.title;
      button.addEventListener("click", function () {
        loadConversation(conversation.id);
      });

      const time = document.createElement("span");
      time.textContent = new Date(conversation.created_at).toLocaleString();

      info.appendChild(button);
      info.appendChild(time);

      const actions = document.createElement("div");
      actions.className = "doc-actions";

      const renameButton = document.createElement("button");
      renameButton.className = "mini secondary";
      renameButton.textContent = "重命名";
      renameButton.addEventListener("click", function () {
        renameConversation(conversation.id, conversation.title);
      });

      const deleteButton = document.createElement("button");
      deleteButton.className = "mini danger";
      deleteButton.textContent = "删除";
      deleteButton.addEventListener("click", function () {
        deleteConversation(conversation.id);
      });

      actions.appendChild(renameButton);
      actions.appendChild(deleteButton);
      item.appendChild(checkbox);
      item.appendChild(info);
      item.appendChild(actions);
      list.appendChild(item);
    });

    state.currentConversationIds = currentIds;
    state.convTotal = page.total;
    const currentPage = Math.floor(state.convOffset / state.convLimit) + 1;
    const totalPages = Math.max(1, Math.ceil(page.total / state.convLimit));
    document.getElementById("conv-page-info").textContent =
      "第 " + currentPage + " / " + totalPages + " 页，共 " + page.total + " 个会话";
    document.getElementById("conv-prev-btn").disabled = state.convOffset <= 0;
    document.getElementById("conv-next-btn").disabled =
      state.convOffset + state.convLimit >= page.total;
    updateConvSelectAll();
  } catch (error) {
    console.error(error);
  }
}

async function renameConversation(conversationId, currentTitle) {
  const title = prompt("输入新的会话标题", currentTitle);
  if (!title) {
    return;
  }
  try {
    await request("/api/v1/chat/conversations/" + conversationId, {
      method: "PATCH",
      body: JSON.stringify({ title: title }),
    });
    showToast("会话已重命名", "success");
    await loadConversations();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteConversation(conversationId) {
  if (!confirm("确定删除这个会话吗？")) {
    return;
  }
  try {
    await request("/api/v1/chat/conversations/" + conversationId, { method: "DELETE" });
    if (state.conversationId === conversationId) {
      newChat();
    }
    showToast("会话已删除", "success");
    await loadConversations();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadConversation(conversationId) {
  if (state.streaming) {
    stopGeneration();
    showToast("已停止上一轮生成", "success");
  }
  try {
    const detail = await request("/api/v1/chat/conversations/" + conversationId);
    state.conversationId = detail.id;
    const container = document.getElementById("chat-messages");
    container.innerHTML = "";
    detail.messages.forEach(function (message) {
      createMessageBubble(message.role, message.content, message.citations || []);
    });
    showToast("已加载历史会话", "success");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function createMessageBubble(role, content, citations) {
  const container = document.getElementById("chat-messages");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble " + role;

  const body = document.createElement("div");
  body.className = "message-body";
  body.innerHTML = renderMarkdown(content || "");
  bubble.appendChild(body);

  if (citations && citations.length) {
    const row = document.createElement("div");
    row.className = "citations-row";
    renderCitationChips(row, citations);
    bubble.appendChild(row);
  }

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
  return bubble;
}

function renderCitationChips(row, citations) {
  row.innerHTML = "";
  citations.forEach(function (citation) {
    const chip = document.createElement("button");
    chip.className = "citation-chip";
    chip.textContent = "[" + citation.index + "] 引用";
    chip.addEventListener("click", function () {
      openCitationModal(citation);
    });
    row.appendChild(chip);
  });
}

function openCitationModal(citation) {
  const modal = document.getElementById("citation-modal");
  const content = document.getElementById("citation-content");
  content.textContent = citation.content;
  modal.classList.remove("hidden");
}

function closeCitationModal() {
  document.getElementById("citation-modal").classList.add("hidden");
}

function scheduleMarkdownRender(element) {
  if (state.renderTimer) {
    return;
  }
  state.renderTimer = setTimeout(function () {
    state.renderTimer = null;
    element.innerHTML = renderMarkdown(state.answerBuffer);
    const container = document.getElementById("chat-messages");
    container.scrollTop = container.scrollHeight;
  }, 80);
}

function updateStopButton() {
  const button = document.getElementById("stop-btn");
  button.classList.toggle("hidden", !state.streaming);
}

async function ask() {
  const input = document.getElementById("query");
  const query = input.value.trim();
  if (!query) {
    return;
  }
  if (state.streaming) {
    showToast("正在生成回答，请先停止生成或等待完成", "error");
    return;
  }

  createMessageBubble("user", query, []);
  input.value = "";

  const assistantBubble = createMessageBubble("assistant", "", []);
  assistantBubble.classList.add("streaming");
  const body = assistantBubble.querySelector(".message-body");
  const citationsRow = document.createElement("div");
  citationsRow.className = "citations-row";
  assistantBubble.appendChild(citationsRow);

  state.answerBuffer = "";
  state.streaming = true;
  state.streamAbort = new AbortController();
  updateStopButton();

  try {
    const response = await fetch("/api/v1/chat/stream", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        query: query,
        conversation_id: state.conversationId,
        top_k: 5,
      }),
      signal: state.streamAbort.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error("请求失败：" + response.status);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const read = await reader.read();
      if (read.done) {
        break;
      }
      buffer += decoder.decode(read.value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const lines = part.split("\n");
        let eventName = "message";
        let dataText = "";
        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          }
          if (line.startsWith("data:")) {
            dataText += line.slice(5).trim();
          }
        }
        if (!dataText) {
          continue;
        }
        const payload = JSON.parse(dataText);
        if (eventName === "citations") {
          renderCitationChips(citationsRow, payload.citations || []);
        }
        if (eventName === "token") {
          state.answerBuffer += payload.text || "";
          scheduleMarkdownRender(body);
        }
        if (eventName === "error") {
          state.answerBuffer += "\n\n**错误：** " + (payload.message || "未知错误");
          body.innerHTML = renderMarkdown(state.answerBuffer);
          showToast(payload.message || "请求失败", "error");
        }
        if (eventName === "done") {
          state.conversationId = payload.conversation_id || state.conversationId;
        }
      }
    }
    body.innerHTML = renderMarkdown(state.answerBuffer);
  } catch (error) {
    if (error.name === "AbortError") {
      body.innerHTML = renderMarkdown(state.answerBuffer + "\n\n_已停止生成_");
    } else {
      body.innerHTML = renderMarkdown("请求失败：" + error.message);
      showToast(error.message, "error");
    }
  } finally {
    assistantBubble.classList.remove("streaming");
    state.streaming = false;
    state.streamAbort = null;
    updateStopButton();
    await loadConversations();
  }
}

function stopGeneration() {
  if (state.streamAbort) {
    state.streamAbort.abort();
  }
}

function newChat() {
  if (state.streaming) {
    stopGeneration();
  }
  state.conversationId = null;
  document.getElementById("chat-messages").innerHTML = "";
}

function formatMetric(value) {
  if (typeof value !== "number") {
    return String(value);
  }
  return value <= 1 ? (value * 100).toFixed(1) + "%" : value.toFixed(1);
}

function renderEvalTrend(runs) {
  const container = document.getElementById("eval-trend");
  container.innerHTML = "";
  if (!runs.length) {
    container.textContent = "暂无趋势数据";
    return;
  }
  const ordered = runs.slice().reverse();
  const chart = document.createElement("div");
  chart.className = "trend-bars";
  ordered.forEach(function (run) {
    const column = document.createElement("div");
    column.className = "trend-column";

    const group = document.createElement("div");
    group.className = "trend-bar-group";

    const hitBar = document.createElement("div");
    hitBar.className = "trend-bar hit";
    hitBar.style.height = Math.max(4, run.hit_rate * 100) + "%";
    hitBar.title = "hit_rate " + (run.hit_rate * 100).toFixed(1) + "%";

    const mrrBar = document.createElement("div");
    mrrBar.className = "trend-bar mrr";
    mrrBar.style.height = Math.max(4, run.mrr * 100) + "%";
    mrrBar.title = "MRR " + run.mrr.toFixed(3);

    group.appendChild(hitBar);
    group.appendChild(mrrBar);

    const label = document.createElement("span");
    label.textContent = new Date(run.created_at).toLocaleTimeString();

    column.appendChild(group);
    column.appendChild(label);
    chart.appendChild(column);
  });
  container.appendChild(chart);
}

async function loadEvalRuns() {
  try {
    const runs = await request("/api/v1/eval/runs?limit=10");
    renderEvalTrend(runs);
    const container = document.getElementById("eval-history");
    container.innerHTML = "";
    if (!runs.length) {
      container.textContent = "暂无评测记录";
      return;
    }
    runs.forEach(function (run) {
      const item = document.createElement("div");
      item.className = "eval-run";
      const title = document.createElement("strong");
      title.textContent = run.dataset_name + " · " + new Date(run.created_at).toLocaleString();
      const metrics = document.createElement("span");
      metrics.textContent =
        "hit_rate " + (run.hit_rate * 100).toFixed(1) + "% · MRR " + run.mrr.toFixed(3);
      item.appendChild(title);
      item.appendChild(metrics);
      container.appendChild(item);
    });
  } catch (error) {
    console.error(error);
  }
}

async function runEval() {
  const output = document.getElementById("eval-result");
  output.textContent = "评测运行中...";
  try {
    const data = await request("/api/v1/eval/runs", {
      method: "POST",
      body: JSON.stringify({ dataset_name: "rag_benchmark", top_k: 5 }),
    });
    output.innerHTML = "";
    const grid = document.createElement("div");
    grid.className = "metric-grid";
    Object.keys(data.metrics).forEach(function (key) {
      const card = document.createElement("div");
      card.className = "metric-card";
      const value = document.createElement("strong");
      value.textContent = formatMetric(data.metrics[key]);
      const label = document.createElement("span");
      label.textContent = key;
      card.appendChild(value);
      card.appendChild(label);
      grid.appendChild(card);
    });
    output.appendChild(grid);
    await loadEvalRuns();
  } catch (error) {
    output.textContent = error.message;
    showToast(error.message, "error");
  }
}

function scheduleDocumentPolling() {
  setInterval(function () {
    if (state.user) {
      loadDocuments(true);
    }
  }, 5000);
}

document.getElementById("login-tab").addEventListener("click", function () {
  switchAuthTab("login");
});
document.getElementById("register-tab").addEventListener("click", function () {
  switchAuthTab("register");
});
document.getElementById("login-btn").addEventListener("click", login);
document.getElementById("register-btn").addEventListener("click", register);
document.getElementById("logout-btn").addEventListener("click", logout);
document.getElementById("upload-btn").addEventListener("click", uploadDocument);
document.getElementById("refresh-btn").addEventListener("click", function () {
  loadDocuments();
});
document.getElementById("history-btn").addEventListener("click", loadConversations);
document.getElementById("ask-btn").addEventListener("click", ask);
document.getElementById("stop-btn").addEventListener("click", stopGeneration);
document.getElementById("new-chat-btn").addEventListener("click", newChat);
document.getElementById("eval-btn").addEventListener("click", runEval);
document.getElementById("eval-history-btn").addEventListener("click", loadEvalRuns);
document.getElementById("reingest-all-btn").addEventListener("click", reingestAllDocuments);
document.getElementById("doc-select-all").addEventListener("change", function () {
  setDocumentCheckboxes(this.checked);
});
document.getElementById("doc-bulk-delete-btn").addEventListener("click", bulkDeleteDocuments);
document.getElementById("conv-select-all").addEventListener("change", function () {
  setConversationCheckboxes(this.checked);
});
document.getElementById("conv-bulk-delete-btn").addEventListener("click", bulkDeleteConversations);
document.getElementById("citation-close").addEventListener("click", closeCitationModal);
document.getElementById("citation-modal").addEventListener("click", function (event) {
  if (event.target.id === "citation-modal") {
    closeCitationModal();
  }
});
document.getElementById("query").addEventListener("keydown", function (event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    ask();
  }
});
document.getElementById("doc-search-btn").addEventListener("click", function () {
  state.docQuery = document.getElementById("doc-search").value.trim();
  state.docOffset = 0;
  loadDocuments();
});
document.getElementById("doc-search").addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    state.docQuery = document.getElementById("doc-search").value.trim();
    state.docOffset = 0;
    loadDocuments();
  }
});
document.getElementById("doc-prev-btn").addEventListener("click", function () {
  state.docOffset = Math.max(0, state.docOffset - state.docLimit);
  loadDocuments();
});
document.getElementById("doc-next-btn").addEventListener("click", function () {
  state.docOffset = state.docOffset + state.docLimit;
  loadDocuments();
});
document.getElementById("conv-search-btn").addEventListener("click", function () {
  state.convQuery = document.getElementById("conv-search").value.trim();
  state.convOffset = 0;
  loadConversations();
});
document.getElementById("conv-search").addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    state.convQuery = document.getElementById("conv-search").value.trim();
    state.convOffset = 0;
    loadConversations();
  }
});
document.getElementById("conv-prev-btn").addEventListener("click", function () {
  state.convOffset = Math.max(0, state.convOffset - state.convLimit);
  loadConversations();
});
document.getElementById("conv-next-btn").addEventListener("click", function () {
  state.convOffset = state.convOffset + state.convLimit;
  loadConversations();
});

const dropZone = document.getElementById("drop-zone");
dropZone.addEventListener("dragover", function (event) {
  event.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", function () {
  dropZone.classList.remove("dragover");
});
dropZone.addEventListener("drop", function (event) {
  event.preventDefault();
  dropZone.classList.remove("dragover");
  const input = document.getElementById("file-input");
  input.files = event.dataTransfer.files;
  if (input.files.length) {
    showToast("已选择 " + input.files[0].name, "success");
  }
});

checkDatabase();
checkProvider();
loadMe().then(function () {
  if (state.user) {
    loadDocuments();
    loadConversations();
    loadEvalRuns();
  }
});
scheduleDocumentPolling();
