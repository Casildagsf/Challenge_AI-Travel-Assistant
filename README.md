# 🌍 AI Travel Advisor

**Live app: <https://challenge-ai-travel-assistant.vercel.app>**
**API: <https://ai-travel-assistant-4lhq.onrender.com>** ([docs](https://ai-travel-assistant-4lhq.onrender.com/docs))

A trip planner that writes a day-by-day itinerary grounded in **real external
data** — historical weather and live exchange rates — rather than only what the
model remembers.

Built for the Ironhack AI Engineering week-5 challenge.

> The app is behind an access code, since every plan costs real money to
> generate. Ask Casilda for it.

## How it is put together

```
Browser (Vercel)                Render                    OpenAI
────────────────                ──────                    ──────
React form                      FastAPI
  access code  ──X-API-Key──►   auth gate
                                gather_facts ──────────►  Open-Meteo
                                                          open.er-api.com
                                build_itinerary ───────►  gpt-4o
  renders JSON ◄─────────────   summarise
```

The OpenAI key lives only on Render. The browser talks to this API and never to
OpenAI, so the key is never in the shipped JavaScript.

The access code is typed by the user and kept in `localStorage`. That matters:
anything baked into a `VITE_*` build variable is readable by anyone who opens
the bundle, so a secret cannot live in the front end.

## What it does

1. **Collects** the trip in a form: country, length, month, interests, and
   optionally the cities you'll sleep in.
2. **Chooses the cities for you** if you don't know them — give it "Scotland,
   14 days" and it picks the bases and splits the nights.
3. **Retrieves** real data: climate averages for that month and a live
   local-currency → EUR rate.
4. **Plans** a day-by-day itinerary with accommodation per city, a budget in
   the local currency, and practical tips.
5. **Reports** the tokens and the money it just spent.

A typical trip costs about **$0.02** and takes 30–60 seconds. On Render's free
tier the first request after 15 idle minutes also waits ~50s for a cold start.

## API

| Method | Path | Auth | Notes |
|---|---|---|---|
| `GET` | `/` | — | What this service is |
| `GET` | `/health` | — | No model calls; use it to check a deploy is alive |
| `GET` | `/docs` | — | Swagger UI, generated from the type hints |
| `POST` | `/plan` | `X-API-Key` | The whole planning run |

Only `country`, `days` and `month` are required. Leave `nights_per_city` empty
to have the cities chosen for you.

```bash
curl -X POST https://ai-travel-assistant-4lhq.onrender.com/plan \
  -H 'Content-Type: application/json' -H 'X-API-Key: ...' \
  -d '{"country":"Scotland","days":9,"month":"May","interests":["hiking"]}'
```

`/plan` fails closed: if `APP_API_KEY` is not set on the server it returns 503
rather than serving unprotected.

## Two models, on purpose

| Job | Model | Why |
|---|---|---|
| Itinerary, JSON structuring, choosing cities | `gpt-4o` | Needs real world knowledge and care |
| Images (notebook only) | `gpt-image-1` | Poster at `medium`, daily images at `low` |

Image generation is not in the deployed app — it takes minutes and risks the
free tier's request limits. It still works in the notebook.

## Data sources (no API keys needed)

| Tool | Source | Returns |
|---|---|---|
| `get_weather` | [Open-Meteo archive](https://open-meteo.com/) | Average high/low and rainy days for that month, from 2021–2025 daily records |
| `get_exchange_rate` | [Frankfurter](https://frankfurter.dev/) (ECB), falling back to [open.er-api.com](https://open.er-api.com/) | Live local-currency → EUR rate |
| `get_transport` | OpenAI web search | Real journey time and ticket cost between cities |
| `geocode` | Open-Meteo geocoding | Coordinates, filtered by country or region |

**Weather is climate data, not a forecast.** Forecasts only reach ~16 days ahead
and these trips are months away, so the tool averages five years of real records
for that month and says so.

## Things learned the hard way

- **Never let the model count.** Asking for "exactly N days" produced 3 days for
  a 6-day trip. The day-to-city allocation is computed in Python and handed over
  as a fixed list. When the model proposes a city split, Python still checks the
  nights add up and corrects them.
- **Geocoding needs a country — and "country" is not what people type.**
  `"Galicia"` alone resolves to a village of 416 people in Chiapas, Mexico. But
  filtering on the country field alone broke `"Scotland"`, which the geocoder
  files under `country: United Kingdom, admin1: Scotland`. Match the region
  field too.
- **Population sorting picks countries over cities.** `"Santo Domingo"` resolved
  to the country entity (10.6M) rather than the capital (2.2M), reporting 20°C
  for a Caribbean January. Filter to populated places first.
- **One data failure looks like several unrelated bugs.** When geocoding failed,
  the weather panel emptied, the planner had no currency code so it printed the
  literal `CUR` placeholder from the prompt, and the accommodation section
  vanished. One cause, three symptoms.
- **A model given no facts invents them fluently**, and an itinerary written
  without data reads exactly as confidently as one written with it. Failed
  lookups are now shown to the traveller instead of silently disappearing.
- **The schema is the bottleneck, not the planner.** Anything missing from
  `SUMMARY_PROMPT`'s JSON shape is invisible in the UI even when it is correct
  in the prose. That is how the EUR budget total and the per-city accommodation
  both went missing.
- **A currency API is not a currency API.** Frankfurter serves ECB reference
  rates: about 30 currencies. DOP, EGP, PEN and ~130 others need another source.

## Running it locally

Two servers. The backend:

```bash
pip install -r requirements-api.txt
echo 'OPENAI_API_KEY=sk-...' > .env.local
echo "APP_API_KEY=$(python -c 'import secrets;print(secrets.token_urlsafe(32))')" >> .env.local
uvicorn api.main:app --reload            # http://localhost:8000/docs
```

The front end, in a second terminal:

```bash
cd web
npm install
echo 'VITE_API_BASE=http://localhost:8000' > .env.local
npm run dev                              # http://localhost:5173
```

`.env.local` is gitignored in both places. Unlock the UI with the `APP_API_KEY`
value.

## Deployment

**Backend — Render**, from this repo:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements-api.txt` |
| Start command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Env vars | `OPENAI_API_KEY`, `APP_API_KEY`, `ALLOWED_ORIGINS` |

`--host 0.0.0.0` and `$PORT` are both required; the defaults make the service
unreachable.

**Front end — Vercel**, from the same repo:

| Setting | Value |
|---|---|
| Root directory | `web` |
| Framework | Vite |
| Env var | `VITE_API_BASE` = the Render URL, no trailing slash |

`ALLOWED_ORIGINS` is a comma-separated CORS allowlist — the Vercel domain plus
`http://localhost:5173`. Vercel preview deployments get their own URLs and are
therefore blocked; that is expected.

Both platforms deploy on push to `main`. Keep them in step: a front end that
deploys while the API does not will send fields the old API rejects.

## Files

| File | What it is |
|---|---|
| `api/main.py` | FastAPI app: request/response models, auth, the `/plan` endpoint |
| `travel_assistant.py` | All the logic: tools, city picking, itinerary, images, costing |
| `web/` | React front end (Vite) |
| `requirements-api.txt` | Python dependencies |
| `TravelAssisstant.ipynb` | The original notebook this grew out of |
| `project-brief-ai-travel-advisor.md` | The assignment |

An earlier version of this project was a Gradio app on Hugging Face Spaces. It
was replaced by the split above; the logic in `travel_assistant.py` is the same
code both versions called.
