import { useState, useMemo } from "react";

const row = { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" };

export default function SessionComposer({ repositories, agents, sessions, onCreate }) {
  const [repoId, setRepoId] = useState("");
  const [agentId, setAgentId] = useState("");
  const [model, setModel] = useState("gpt-5-mini");
  const [thinkingEffort, setThinkingEffort] = useState("medium");
  const [mode, setMode] = useState("plan");

  // Derive available options from the selected agent
  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === agentId) || agents[0],
    [agents, agentId],
  );

  const efforts = selectedAgent?.supported_thinking_efforts || [];
  const modes = selectedAgent?.supported_modes || [];

  // Auto-select first agent if none selected
  const effectiveAgentId = agentId || (agents[0]?.id ?? "");

  return (
    <>
      <h2>Session Composer</h2>
      <div style={row}>
        <select value={repoId} onChange={(e) => setRepoId(e.target.value)}>
          <option value="">No repository</option>
          {repositories.map((r) => (
            <option key={r.id} value={r.id}>
              {r.url}
            </option>
          ))}
        </select>

        <select
          value={effectiveAgentId}
          onChange={(e) => {
            setAgentId(e.target.value);
            // Reset to first valid values when agent changes
            const a = agents.find((a) => a.id === e.target.value);
            if (a) {
              if (!a.supported_thinking_efforts.includes(thinkingEffort)) {
                setThinkingEffort(a.supported_thinking_efforts[0] || "medium");
              }
              if (!a.supported_modes.includes(mode)) {
                setMode(a.supported_modes[0] || "plan");
              }
            }
          }}
        >
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.id})
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
            onCreate({
              repository_id: repoId || null,
              agent_id: effectiveAgentId,
              model,
              thinking_effort: thinkingEffort,
              mode,
            })
          }
        >
          Start session
        </button>
      </div>

      <ul>
        {sessions.map((s) => (
          <li key={s.id}>
            {s.id.slice(0, 8)} | {s.agent_id} | {s.model} | {s.thinking_effort} | {s.mode}
          </li>
        ))}
      </ul>
    </>
  );
}
