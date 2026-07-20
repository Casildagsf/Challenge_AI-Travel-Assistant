import { useState } from "react";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];

export default function TripForm({ onSubmit, loading }) {
  const [destination, setDestination] = useState("Andalusia");
  const [country, setCountry] = useState("Spain");
  const [month, setMonth] = useState("September");
  const [transport, setTransport] = useState("train");
  const [interests, setInterests] = useState("food, history");
  const [constraints, setConstraints] = useState("");
  // The backend organises a trip around cities slept in, so that is what we
  // collect - not a free-text "where to".
  const [cities, setCities] = useState([{ name: "Seville", nights: 3 }]);

  const days = cities.reduce((sum, c) => sum + (Number(c.nights) || 0), 0);

  function setCity(i, patch) {
    setCities(cities.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  }

  function submit(e) {
    e.preventDefault();
    const nights_per_city = {};
    for (const c of cities) {
      const name = c.name.trim();
      if (name) nights_per_city[name] = Number(c.nights) || 0;
    }
    onSubmit({
      destination: destination.trim(),
      country: country.trim(),
      days,
      nights_per_city,
      inter_city_transport: transport,
      month,
      interests: interests.split(",").map((s) => s.trim()).filter(Boolean),
      constraints: constraints.trim(),
    });
  }

  const valid = days > 0 && days <= 30 &&
    cities.some((c) => c.name.trim()) && destination.trim() && country.trim();

  return (
    <form className="card trip-form" onSubmit={submit}>
      <div className="row">
        <label>
          Region or area
          <input value={destination} onChange={(e) => setDestination(e.target.value)} />
        </label>
        <label>
          Country
          <input value={country} onChange={(e) => setCountry(e.target.value)} />
        </label>
      </div>

      <fieldset>
        <legend>Cities you'll sleep in</legend>
        {cities.map((c, i) => (
          <div className="row city-row" key={i}>
            <input
              placeholder="City or town"
              value={c.name}
              onChange={(e) => setCity(i, { name: e.target.value })}
            />
            <input
              type="number" min="1" max="30" className="nights"
              value={c.nights}
              onChange={(e) => setCity(i, { nights: e.target.value })}
            />
            <span className="unit">nights</span>
            {cities.length > 1 && (
              <button type="button" className="linkish"
                onClick={() => setCities(cities.filter((_, j) => j !== i))}>
                remove
              </button>
            )}
          </div>
        ))}
        <button type="button" className="linkish"
          onClick={() => setCities([...cities, { name: "", nights: 2 }])}>
          + add another city
        </button>
        <p className="muted small">
          Total trip length: <strong>{days} days</strong>
          {cities.length > 1 && " — a second city adds a web search for transport."}
        </p>
      </fieldset>

      <div className="row">
        <label>
          Month
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            {MONTHS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <label>
          Travel between cities
          <select value={transport} onChange={(e) => setTransport(e.target.value)}>
            <option>train</option><option>car</option>
            <option>bus</option><option>plane</option><option>walking</option>
          </select>
        </label>
      </div>

      <label>
        Interests <span className="muted small">(comma separated)</span>
        <input value={interests} onChange={(e) => setInterests(e.target.value)} />
      </label>

      <label>
        Constraints <span className="muted small">(diet, mobility, kids… optional)</span>
        <input value={constraints} onChange={(e) => setConstraints(e.target.value)} />
      </label>

      <button type="submit" className="primary" disabled={loading || !valid}>
        {loading ? "Planning…" : "Plan my trip 🧳"}
      </button>
      {days > 30 && <p className="error-inline">Maximum trip length is 30 days.</p>}
    </form>
  );
}
