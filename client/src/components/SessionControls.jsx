import { useState, useMemo } from "react";

const row = { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center", marginBottom: "0.5rem" };

export default function SessionControls({
  sessions,
  agents,
  selectedSession,
  onSelectSession,
  onUpdate,
  onUpdateTools,
}) {
  const [model, setModel] = useState("gpt-5-mini");
  const [thinkingEffort, setThinkingEffort] = useState("medium");
  const [mode, setMode] = useState("plan");
  const [tools, setTools] = useState("");

  // Determine the agent for the selected session so we can show valid options
  const currentSession = useMemo(
    () => sessions.find((s) => s.id === selectedSession),
    [sessions, selectedSession],
  );
  const agent = useMemo(
    () => agents.find((a) => a.id === currentSession?.agent_id),
    [agents, currentSession],
  );

  const efforts = agent?.supported_thinking_efforts || ["low", "medium", "high"];
  const modes = agent?.supported_modes || ["plan", "build", "chat"];

  return (
    <>
      <h2>Session Controls</h2>
      <div style={row}>
        <select
          value={selectedSession}
          onChange={(e) => onSelectSession(e.target.value)}
        >
          <option value="">Select session</option>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.id.slice(0, 8)} ({s.agent_id})
            </option>
          ))}
        </select>

        <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="model" />

        <select value={thinkingEffort} onChange={(e) => setThinkingEffort(e.target.value)}>
          {efforts.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>

        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          {modes.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        <button
          onClick={() =>
            selectedSession &&
            onUpdate(selectedSession, {
              model,
              thinking_effort: thinkingEffort,
              mode,
            })
          }
        >
          Apply
        </button>
      </div>

      <div style={row}>
        <input
          placeholder="comma separated tools"
          value={tools}
          onChange={(e) => setTools(e.target.value)}
        />
        <button
          onClick={() => {
            if (!selectedSession) return;
            const list = tools
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean);
            onUpdateTools(selectedSession, list);
          }}
        >
          Update allowed tools
        </button>
      </div>
    </>
  );
}
