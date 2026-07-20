import { useState } from "react";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];

export default function TripForm({ onSubmit, loading }) {
  const [country, setCountry] = useState("Spain");
  const [destination, setDestination] = useState("");
  const [month, setMonth] = useState("September");
  const [transport, setTransport] = useState("train");
  const [interests, setInterests] = useState("food, history");

  // Two ways to say where you're sleeping: name the cities yourself, or give a
  // total number of days and let the planner choose them.
  const [chooseForMe, setChooseForMe] = useState(false);
  const [totalDays, setTotalDays] = useState(7);
  const [cities, setCities] = useState([{ name: "Seville", nights: 3 }]);

  const [travellingAs, setTravellingAs] = useState("");
  const [accommodation, setAccommodation] = useState("");
  const [mustSee, setMustSee] = useState("");
  const [avoid, setAvoid] = useState("");
  const [dietary, setDietary] = useState("");
  const [mobility, setMobility] = useState("");
  const [constraints, setConstraints] = useState("");
  const [more, setMore] = useState(false);

  const cityDays = cities.reduce((sum, c) => sum + (Number(c.nights) || 0), 0);
  const days = chooseForMe ? Number(totalDays) || 0 : cityDays;
  const namedCities = cities.filter((c) => c.name.trim()).length;
  // The planner may pick several cities, so we can't know yet whether transport
  // matters - ask for a preference, but only when it could possibly apply.
  const transportRelevant = chooseForMe ? days > 3 : namedCities > 1;

  function setCity(i, patch) {
    setCities(cities.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  }

  function submit(e) {
    e.preventDefault();
    const nights_per_city = {};
    if (!chooseForMe) {
      for (const c of cities) {
        const name = c.name.trim();
        if (name) nights_per_city[name] = Number(c.nights) || 0;
      }
    }
    onSubmit({
      country: country.trim(),
      days,
      month,
      // Empty object tells the API to choose the cities itself.
      nights_per_city,
      destination: destination.trim() || null,
      inter_city_transport: transportRelevant ? transport : null,
      interests: interests.split(",").map((s) => s.trim()).filter(Boolean),
      constraints: constraints.trim(),
      travelling_as: travellingAs.trim(),
      accommodation_style: accommodation.trim(),
      must_see: mustSee.trim(),
      avoid: avoid.trim(),
      dietary: dietary.trim(),
      mobility: mobility.trim(),
    });
  }

  const valid = country.trim() && days > 0 && days <= 30 &&
    (chooseForMe || namedCities > 0);

  return (
    <form className="card trip-form" onSubmit={submit}>
      <div className="row">
        <label>
          Country
          <input value={country} onChange={(e) => setCountry(e.target.value)} />
        </label>
        <label>
          Region or area <span className="muted small">(optional)</span>
          <input
            value={destination}
            placeholder="e.g. Andalusia — leave blank if unsure"
            onChange={(e) => setDestination(e.target.value)}
          />
        </label>
      </div>

      <fieldset>
        <legend>Where you'll sleep</legend>

        <label className="check">
          <input
            type="checkbox"
            checked={chooseForMe}
            onChange={(e) => setChooseForMe(e.target.checked)}
          />
          I don't know the cities — choose them for me
        </label>

        {chooseForMe ? (
          <div className="row city-row">
            <span>Total trip length</span>
            <input
              type="number" min="1" max="30" className="nights"
              value={totalDays}
              onChange={(e) => setTotalDays(e.target.value)}
            />
            <span className="unit">days</span>
          </div>
        ) : (
          <>
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
          </>
        )}

        <p className="muted small">
          {chooseForMe
            ? `The planner will pick the bases and split ${days || 0} days between them.`
            : `Total trip length: ${days} days`}
        </p>
      </fieldset>

      <div className="row">
        <label>
          Month
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            {MONTHS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        {transportRelevant && (
          <label>
            Travel between cities
            <select value={transport} onChange={(e) => setTransport(e.target.value)}>
              <option>train</option><option>car</option>
              <option>bus</option><option>plane</option><option>walking</option>
            </select>
          </label>
        )}
      </div>

      <label>
        Interests <span className="muted small">(comma separated)</span>
        <input value={interests} onChange={(e) => setInterests(e.target.value)} />
      </label>

      <button type="button" className="linkish" onClick={() => setMore(!more)}>
        {more ? "− fewer options" : "+ more options"}
      </button>

      {more && (
        <div className="more">
          <div className="row">
            <label>
              Who's travelling
              <input value={travellingAs} placeholder="a couple, family with a 7-year-old…"
                onChange={(e) => setTravellingAs(e.target.value)} />
            </label>
            <label>
              Accommodation style
              <input value={accommodation} placeholder="small hotels, apartments…"
                onChange={(e) => setAccommodation(e.target.value)} />
            </label>
          </div>
          <label>
            Must see
            <input value={mustSee} placeholder="places you already know you want"
              onChange={(e) => setMustSee(e.target.value)} />
          </label>
          <label>
            Avoid
            <input value={avoid} placeholder="no early starts, no big crowds…"
              onChange={(e) => setAvoid(e.target.value)} />
          </label>
          <div className="row">
            <label>
              Dietary needs
              <input value={dietary} placeholder="vegetarian, no shellfish…"
                onChange={(e) => setDietary(e.target.value)} />
            </label>
            <label>
              Mobility
              <input value={mobility} placeholder="limited walking, step-free…"
                onChange={(e) => setMobility(e.target.value)} />
            </label>
          </div>
          <label>
            Anything else
            <input value={constraints} placeholder="pace, budget, allergies…"
              onChange={(e) => setConstraints(e.target.value)} />
          </label>
        </div>
      )}

      <button type="submit" className="primary" disabled={loading || !valid}>
        {loading ? "Planning…" : "Plan my trip 🧳"}
      </button>
      {days > 30 && <p className="error-inline">Maximum trip length is 30 days.</p>}
    </form>
  );
}
