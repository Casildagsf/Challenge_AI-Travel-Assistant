// Where the backend lives. Not a secret - it's a public URL, and anyone can
// see it in the network tab anyway. Override with VITE_API_BASE for local work.
export const BASE =
  import.meta.env.VITE_API_BASE ?? "https://ai-travel-assistant-4lhq.onrender.com";

/** Pull the useful message out of a FastAPI error response. */
async function errorFrom(res) {
  let detail;
  try {
    detail = (await res.json()).detail;
  } catch {
    detail = await res.text();
  }
  if (Array.isArray(detail)) {
    // 422 validation errors arrive as a list of {loc, msg}
    return detail.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return typeof detail === "string" ? detail : `HTTP ${res.status}`;
}

/**
 * Check an access code without spending anything.
 *
 * The trick: send a deliberately invalid body (days: 0 fails the gt=0 rule).
 * Auth runs before validation, so 401 means the code is wrong, while 422 means
 * the code was accepted and only the body was rejected. No model ever runs.
 */
export async function verifyCode(code) {
  const res = await fetch(`${BASE}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": code },
    body: JSON.stringify({
      destination: "x", country: "Spain", days: 0,
      nights_per_city: { x: 1 }, inter_city_transport: "train",
      month: "May", interests: [], constraints: "",
    }),
  });
  if (res.status === 422) return true;
  if (res.status === 401) return false;
  throw new Error(await errorFrom(res));
}

export async function planTrip(trip, code) {
  const res = await fetch(`${BASE}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": code },
    body: JSON.stringify(trip),
  });
  if (!res.ok) throw new Error(await errorFrom(res));
  return res.json();
}
