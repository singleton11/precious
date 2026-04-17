const statusEl = document.getElementById("status");
const repoList = document.getElementById("repo-list");
const repoSelect = document.getElementById("repository-id");
const agentSelect = document.getElementById("agent-id");
const sessionList = document.getElementById("session-list");
const sessionSelect = document.getElementById("session-id");
const logList = document.getElementById("log-list");

function password() {
  return document.getElementById("password").value;
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Server-Password": password(),
    ...(options.headers || {}),
  };

  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response.status === 204 ? null : response.json();
}

function setStatus(msg) {
  statusEl.textContent = msg;
}

function option(value, label) {
  const el = document.createElement("option");
  el.value = value;
  el.textContent = label;
  return el;
}

async function loadRepositories() {
  const repositories = await api("/api/repositories");
  repoList.innerHTML = "";

  repoSelect.innerHTML = "";
  repoSelect.appendChild(option("", "No repository"));

  for (const repo of repositories) {
    const li = document.createElement("li");
    li.textContent = `${repo.url} (${repo.id.slice(0, 8)})`;
    repoList.appendChild(li);
    repoSelect.appendChild(option(repo.id, repo.url));
  }
}

async function loadAgents() {
  const agents = await api("/api/agents");
  agentSelect.innerHTML = "";
  for (const agent of agents) {
    agentSelect.appendChild(option(agent.id, `${agent.name} (${agent.id})`));
  }
}

async function loadSessions() {
  const sessions = await api("/api/sessions");
  sessionList.innerHTML = "";
  sessionSelect.innerHTML = "";

  for (const session of sessions) {
    const li = document.createElement("li");
    li.textContent = `${session.id.slice(0, 8)} | ${session.agent_id} | ${session.model} | ${session.thinking_effort} | ${session.mode}`;
    sessionList.appendChild(li);
    sessionSelect.appendChild(option(session.id, session.id));
  }
}

async function loadLogs() {
  const sessionId = sessionSelect.value;
  if (!sessionId) {
    logList.innerHTML = "";
    return;
  }

  const logs = await api(`/api/sessions/${sessionId}/tool-calls`);
  logList.innerHTML = "";
  for (const log of logs) {
    const li = document.createElement("li");
    li.textContent = `${log.name}: ${log.status} (${log.created_at})`;
    logList.appendChild(li);
  }
}

async function refreshAll() {
  await Promise.all([loadRepositories(), loadAgents(), loadSessions()]);
  await loadLogs();
}

document.getElementById("refresh-all").addEventListener("click", async () => {
  try {
    await refreshAll();
    setStatus("Loaded");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("add-repo").addEventListener("click", async () => {
  try {
    await api("/api/repositories", {
      method: "POST",
      body: JSON.stringify({ url: document.getElementById("repo-url").value.trim() }),
    });
    await refreshAll();
    setStatus("Repository added");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("create-session").addEventListener("click", async () => {
  try {
    const repositoryId = repoSelect.value;
    await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({
        repository_id: repositoryId || null,
        agent_id: agentSelect.value,
        model: document.getElementById("model").value,
        thinking_effort: document.getElementById("thinking-effort").value,
        mode: document.getElementById("mode").value,
      }),
    });
    await refreshAll();
    setStatus("Session started");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("update-session").addEventListener("click", async () => {
  try {
    await api(`/api/sessions/${sessionSelect.value}`, {
      method: "PATCH",
      body: JSON.stringify({
        model: document.getElementById("switch-model").value,
        thinking_effort: document.getElementById("switch-thinking").value,
        mode: document.getElementById("switch-mode").value,
      }),
    });
    await refreshAll();
    setStatus("Session updated");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("update-tools").addEventListener("click", async () => {
  try {
    const tools = document
      .getElementById("allowed-tools")
      .value.split(",")
      .map((value) => value.trim())
      .filter(Boolean);

    await api(`/api/sessions/${sessionSelect.value}`, {
      method: "PATCH",
      body: JSON.stringify({ allowed_tools: tools }),
    });
    await refreshAll();
    setStatus("Allowed tools updated");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("add-log").addEventListener("click", async () => {
  try {
    await api(`/api/sessions/${sessionSelect.value}/tool-calls`, {
      method: "POST",
      body: JSON.stringify({
        name: document.getElementById("tool-name").value,
        status: "completed",
      }),
    });
    await loadLogs();
    setStatus("Log added");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("load-logs").addEventListener("click", async () => {
  try {
    await loadLogs();
    setStatus("Logs loaded");
  } catch (error) {
    setStatus(error.message);
  }
});

sessionSelect.addEventListener("change", () => {
  loadLogs().catch((error) => setStatus(error.message));
});

refreshAll().then(() => setStatus("Ready")).catch((error) => setStatus(error.message));
