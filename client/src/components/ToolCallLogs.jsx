import { useState } from "react";

const row = { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" };

export default function ToolCallLogs({ logs, selectedSession, onAddLog, onLoadLogs }) {
  const [toolName, setToolName] = useState("example_tool");

  return (
    <>
      <h2>Tool Call Logs</h2>
      <div style={row}>
        <input
          placeholder="tool name"
          value={toolName}
          onChange={(e) => setToolName(e.target.value)}
        />
        <button
          onClick={() => selectedSession && onAddLog(selectedSession, toolName)}
        >
          Add sample log
        </button>
        <button onClick={onLoadLogs}>Load logs</button>
      </div>
      <ul>
        {logs.map((log) => (
          <li key={log.id}>
            {log.name}: {log.status} ({log.created_at})
          </li>
        ))}
      </ul>
    </>
  );
}
