/**
 * Renders the structured `summary` object rather than the markdown twin.
 * That is exactly why travel_assistant.summarise() exists: prose is for
 * reading, JSON is for building interfaces out of.
 */
export default function Result({ data }) {
  const { summary, facts, total_tokens, cost_usd, cost_eur,
          nights_per_city, cities_were_suggested } = data;
  const allWeather = Object.entries(facts.weather ?? {});
  const weather = allWeather.map(([, w]) => w).filter((w) => !w.error);
  const currency = facts.currency;
  // Silently hiding a failed lookup makes the itinerary look fine while the
  // planner was actually working blind. Say so instead.
  const failures = [
    ...allWeather.filter(([, w]) => w.error).map(([city]) => `weather for ${city}`),
    ...(currency?.error ? ["exchange rate"] : []),
  ];
  const budget = summary.estimated_budget ?? {};

  // Older responses sent a single string for the whole trip. Normalise both
  // shapes to a list so the UI has one thing to render.
  const stays = Array.isArray(summary.accommodation)
    ? summary.accommodation.filter((a) => a && (a.district || a.city))
    : summary.accommodation
      ? [{ city: null, district: null, why: String(summary.accommodation) }]
      : [];
  // Number of nights per base, so each stay can say how long you're there.
  const nightsFor = (city) =>
    Object.entries(nights_per_city ?? {})
      .find(([c]) => c.toLowerCase() === (city ?? "").toLowerCase())?.[1];

  return (
    <div className="result">
      <section className="card">
        <h2>{summary.trip_title}</h2>
        <p className="lede">{summary.trip_summary}</p>
        {cities_were_suggested && nights_per_city && (
          <p className="chosen">
            📍 Bases chosen for you:{" "}
            {Object.entries(nights_per_city)
              .map(([city, n]) => `${city} (${n} ${n === 1 ? "night" : "nights"})`)
              .join(" → ")}
          </p>
        )}
      </section>

      {(weather.length > 0 || currency || failures.length > 0) && (
        <section className="card facts">
          <h3>Real-world data</h3>
          {failures.length > 0 && (
            <p className="warn">
              ⚠️ Could not look up {failures.join(" and ")}. The itinerary below
              was written without {failures.length > 1 ? "them" : "it"}, so treat
              any temperatures or prices in it as guesswork.
            </p>
          )}
          <ul>
            {weather.map((w) => (
              <li key={w.city}>
                🌦️ <strong>{w.city}</strong> in {w.month}: typically{" "}
                {w.avg_high_c}°C / {w.avg_low_c}°C, about {w.rainy_days_in_month}{" "}
                rainy days. <span className="muted small">{w.source}</span>
              </li>
            ))}
            {currency && !currency.error && (
              <li>
                💱 Currency: <strong>{currency.currency}</strong>
                {currency.note
                  ? ` — ${currency.note}`
                  : ` — 1 ${currency.currency} ≈ €${currency.eur_per_unit}`}
                {currency.source && (
                  <span className="muted small"> ({currency.source}
                    {currency.as_of ? `, ${currency.as_of}` : ""})</span>
                )}
              </li>
            )}
            {typeof facts.transport === "string" && (
              <li>🚆 {facts.transport}</li>
            )}
          </ul>
        </section>
      )}

      {stays.length > 0 && (
        <section className="card stays">
          <h3>🏨 Where you'll stay</h3>
          {stays.map((a, i) => {
            const n = nightsFor(a.city);
            return (
              <div className="stay" key={i}>
                {a.district && (
                  <p className="stay-head">
                    <span className="district">{a.district}</span>
                    {a.city && <span className="stay-city">{a.city}</span>}
                    {n && (
                      <span className="stay-nights">
                        {n} {n === 1 ? "night" : "nights"}
                      </span>
                    )}
                  </p>
                )}
                {a.why && <p className="stay-why">{a.why}</p>}
              </div>
            );
          })}
        </section>
      )}

      {(summary.days ?? []).map((d) => (
        <section className="card day" key={d.day}>
          <h3>Day {d.day} — {d.city}</h3>
          {d.theme && <p className="theme">{d.theme}</p>}
          <ul>{(d.do ?? []).map((item, i) => <li key={i}>{item}</li>)}</ul>
          {d.eat && (
            <p className="eat">
              🍽️ <strong>Lunch:</strong> {d.eat.lunch}<br />
              🍷 <strong>Dinner:</strong> {d.eat.dinner}
            </p>
          )}
        </section>
      ))}

      {budget.total && (
        <section className="card">
          <h3>💰 Estimated budget</h3>
          <ul className="budget">
            <li>Lodging: {budget.lodging}</li>
            <li>Food: {budget.food}</li>
            <li>Activities: {budget.activities}</li>
            <li>Transport: {budget.transport}</li>
            <li><strong>Total: {budget.total}</strong></li>
            {budget.total_eur && (
              <li className="eur-total">
                <strong>Total in EUR: {budget.total_eur}</strong>
                {budget.rate_note && (
                  <span className="muted small"> {budget.rate_note}</span>
                )}
              </li>
            )}
          </ul>
        </section>
      )}

      {(summary.tips ?? []).length > 0 && (
        <section className="card">
          <h3>💡 Practical tips</h3>
          <ul>{summary.tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </section>
      )}

      {/* Older backends did not send these, so never assume they are there:
          a front end should not crash because the API is one deploy behind. */}
      {typeof total_tokens === "number" && (
        <p className="muted small cost">
          🧾 {total_tokens.toLocaleString()} tokens — ${cost_usd.toFixed(4)} (≈ €
          {cost_eur.toFixed(4)}) spent generating this plan.
        </p>
      )}
    </div>
  );
}
