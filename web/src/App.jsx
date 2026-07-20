import { useState } from "react";
import { planTrip, verifyCode } from "./api";
import Unlock from "./Unlock";
import TripForm from "./TripForm";
import Result from "./Result";
import "./App.css";

export default function App() {
  // The access code lives in the browser, never in the bundle. Same idea as
  // auth=(user, password) in the Gradio app: the human supplies the secret.
  const [code, setCode] = useState(() => localStorage.getItem("accessCode") ?? "");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function unlock(value) {
    localStorage.setItem("accessCode", value);
    setCode(value);
  }

  function lock() {
    localStorage.removeItem("accessCode");
    setCode("");
    setResult(null);
  }

  async function onPlan(trip) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await planTrip(trip, code));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (!code) return <Unlock onUnlock={unlock} verify={verifyCode} />;

  return (
    <div className="page">
      <header className="site-head">
        <div>
          <h1>🌍 AI Travel Advisor</h1>
          <p className="tagline">
            Planned against real data — historical weather and live exchange rates.
          </p>
        </div>
        <button className="linkish" onClick={lock}>Forget access code</button>
      </header>

      <TripForm onSubmit={onPlan} loading={loading} />

      {error && (
        <div className="error" role="alert">
          <strong>Something went wrong</strong>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p>Gathering weather and currency, then writing your itinerary…</p>
          <p className="muted">
            This takes 30–60 seconds. If the server has been idle, it may need
            another minute to wake up first.
          </p>
        </div>
      )}

      {result && <Result data={result} />}
    </div>
  );
}
