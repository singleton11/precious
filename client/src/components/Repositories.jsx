import { useState } from "react";

const row = { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" };

export default function Repositories({ repositories, onAdd }) {
  const [url, setUrl] = useState("");

  return (
    <>
      <h2>Repositories</h2>
      <div style={row}>
        <input
          placeholder="https://github.com/org/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button
          onClick={async () => {
            await onAdd(url.trim());
            setUrl("");
          }}
        >
          Add repository
        </button>
      </div>
      <ul>
        {repositories.map((r) => (
          <li key={r.id}>
            {r.url} ({r.id.slice(0, 8)})
          </li>
        ))}
      </ul>
    </>
  );
}
