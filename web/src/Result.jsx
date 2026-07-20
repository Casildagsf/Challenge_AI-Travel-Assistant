/**
 * Renders the structured `summary` object rather than the markdown twin.
 * That is exactly why travel_assistant.summarise() exists: prose is for
 * reading, JSON is for building interfaces out of.
 */
export default function Result({ data }) {
  const { summary, facts, total_tokens, cost_usd, cost_eur } = data;
  const weather = Object.values(facts.weather ?? {}).filter((w) => !w.error);
  const currency = facts.currency;
  const budget = summary.estimated_budget ?? {};

  return (
    <div className="result">
      <section className="card">
        <h2>{summary.trip_title}</h2>
        <p className="lede">{summary.trip_summary}</p>
        {summary.accommodation && (
          <p className="muted">🏨 {summary.accommodation}</p>
        )}
      </section>

      {(weather.length > 0 || currency) && (
        <section className="card facts">
          <h3>Real-world data</h3>
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
              </li>
            )}
            {typeof facts.transport === "string" && (
              <li>🚆 {facts.transport}</li>
            )}
          </ul>
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
