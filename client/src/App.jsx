import { useState, useEffect, useCallback } from "react";
import { api, setPassword } from "./api.js";
import ServerAccess from "./components/ServerAccess.jsx";
import Repositories from "./components/Repositories.jsx";
import SessionComposer from "./components/SessionComposer.jsx";
import SessionControls from "./components/SessionControls.jsx";
import ToolCallLogs from "./components/ToolCallLogs.jsx";

const styles = {
  body: { fontFamily: "sans-serif", margin: "2rem" },
  section: {
    marginBottom: "2rem",
    border: "1px solid #ddd",
    padding: "1rem",
    borderRadius: "8px",
  },
  status: { marginTop: "0.5rem", color: "#555" },
};

export default function App() {
  const [status, setStatus] = useState("");
  const [repositories, setRepositories] = useState([]);
  const [agents, setAgents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [logs, setLogs] = useState([]);

  const loadRepositories = useCallback(async () => {
    const data = await api("/api/repositories");
    setRepositories(data);
  }, []);

  const loadAgents = useCallback(async () => {
    const data = await api("/api/agents");
    setAgents(data);
  }, []);

  const loadSessions = useCallback(async () => {
    const data = await api("/api/sessions");
    setSessions(data);
  }, []);

  const loadLogs = useCallback(
    async (sid) => {
      const id = sid || selectedSession;
      if (!id) {
        setLogs([]);
        return;
      }
      const data = await api(`/api/sessions/${id}/tool-calls`);
      setLogs(data);
    },
    [selectedSession],
  );

  const refreshAll = useCallback(async () => {
    await Promise.all([loadRepositories(), loadAgents(), loadSessions()]);
    await loadLogs();
  }, [loadRepositories, loadAgents, loadSessions, loadLogs]);

  useEffect(() => {
    refreshAll()
      .then(() => setStatus("Ready"))
      .catch((e) => setStatus(e.message));
  }, [refreshAll]);

  const handlePasswordChange = (pw) => {
    setPassword(pw);
  };

  const handleRefresh = async () => {
    try {
      await refreshAll();
      setStatus("Loaded");
    } catch (e) {
      setStatus(e.message);
    }
  };

  return (
    <div style={styles.body}>
      <h1>Precious Agent Management</h1>

      <div style={styles.section}>
        <ServerAccess
          onPasswordChange={handlePasswordChange}
          onRefresh={handleRefresh}
        />
        <div style={styles.status}>{status}</div>
      </div>

      <div style={styles.section}>
        <Repositories
          repositories={repositories}
          onAdd={async (url) => {
            await api("/api/repositories", {
              method: "POST",
              body: JSON.stringify({ url }),
            });
            await refreshAll();
            setStatus("Repository added");
          }}
        />
      </div>

      <div style={styles.section}>
        <SessionComposer
          repositories={repositories}
          agents={agents}
          sessions={sessions}
          onCreate={async (payload) => {
            await api("/api/sessions", {
              method: "POST",
              body: JSON.stringify(payload),
            });
            await refreshAll();
            setStatus("Session started");
          }}
        />
      </div>

      <div style={styles.section}>
        <SessionControls
          sessions={sessions}
          agents={agents}
          selectedSession={selectedSession}
          onSelectSession={(id) => {
            setSelectedSession(id);
            loadLogs(id).catch((e) => setStatus(e.message));
          }}
          onUpdate={async (sessionId, payload) => {
            await api(`/api/sessions/${sessionId}`, {
              method: "PATCH",
              body: JSON.stringify(payload),
            });
            await refreshAll();
            setStatus("Session updated");
          }}
          onUpdateTools={async (sessionId, tools) => {
            await api(`/api/sessions/${sessionId}`, {
              method: "PATCH",
              body: JSON.stringify({ allowed_tools: tools }),
            });
            await refreshAll();
            setStatus("Allowed tools updated");
          }}
        />
      </div>

      <div style={styles.section}>
        <ToolCallLogs
          logs={logs}
          selectedSession={selectedSession}
          onAddLog={async (sessionId, name) => {
            await api(`/api/sessions/${sessionId}/tool-calls`, {
              method: "POST",
              body: JSON.stringify({ name, status: "completed" }),
            });
            await loadLogs(sessionId);
            setStatus("Log added");
          }}
          onLoadLogs={() => loadLogs().catch((e) => setStatus(e.message))}
        />
      </div>
    </div>
  );
}
