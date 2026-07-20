import { useState } from "react";

/** Asks for the access code and checks it before letting anyone through. */
export default function Unlock({ onUnlock, verify }) {
  const [value, setValue] = useState("");
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    const code = value.trim();
    if (!code) return;
    setChecking(true);
    setError("");
    try {
      // Costs nothing: see verifyCode in api.js.
      if (await verify(code)) onUnlock(code);
      else setError("That code was not accepted.");
    } catch (err) {
      setError(err.message);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="page unlock">
      <h1>🌍 AI Travel Advisor</h1>
      <p className="tagline">Enter your access code to continue.</p>
      <form onSubmit={submit}>
        <input
          type="password"
          value={value}
          autoFocus
          placeholder="Access code"
          onChange={(e) => setValue(e.target.value)}
        />
        <button type="submit" disabled={checking || !value.trim()}>
          {checking ? "Checking…" : "Unlock"}
        </button>
      </form>
      {error && <p className="error-inline">{error}</p>}
      <p className="muted small">
        Planning a trip costs real money, so the API is not open to everyone.
      </p>
    </div>
  );
}
