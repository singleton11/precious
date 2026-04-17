import { useState } from "react";

const row = { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" };

export default function ServerAccess({ onPasswordChange, onRefresh }) {
  const [pw, setPw] = useState("changeme");

  return (
    <>
      <h2>Server Access</h2>
      <div style={row}>
        <label>
          Password{" "}
          <input
            type="password"
            value={pw}
            onChange={(e) => {
              setPw(e.target.value);
              onPasswordChange(e.target.value);
            }}
          />
        </label>
        <button onClick={onRefresh}>Refresh all</button>
      </div>
    </>
  );
}
