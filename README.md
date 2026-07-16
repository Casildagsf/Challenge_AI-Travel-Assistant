---
title: AI Travel Advisor
emoji: 🌍
colorFrom: indigo
colorTo: pink
sdk: gradio
sdk_version: 6.19.0
app_file: app.py
pinned: false
---

# 🌍 AI Travel Advisor

A conversational trip planner. It collects your preferences in chat, then writes a
day-by-day itinerary grounded in **real external data** — not just what the model
remembers.

Built for the Ironhack AI Engineering week-5 challenge.

## What it does

1. **Collects** destination, dates, interests and constraints in a short chat.
2. **Retrieves** real data: historical weather, live exchange rates, and a web
   search for the journey between cities.
3. **Plans** a day-by-day itinerary with accommodation, budget and tips.
4. **Illustrates** it with a poster for the trip and one image per day.
5. **Reports** the tokens and dollars it just spent.

## Two models, on purpose

| Job | Model | Why |
|---|---|---|
| Conversation, collecting preferences | `gpt-3.5-turbo` | Many short calls, easy task |
| Itinerary, JSON structuring, web search | `gpt-4o` | Needs real world knowledge and care |
| Images | `gpt-image-1` | Poster at `medium`, daily images at `low` |

A typical 4-day trip costs about **$0.11**: roughly $0.001 of chat, $0.02 of
planning, and the rest images.

## Tools (no API keys needed)

| Tool | Source | Returns |
|---|---|---|
| `get_weather` | [Open-Meteo archive](https://open-meteo.com/) | Average high/low and rainy days for that month, from 2021–2025 daily records |
| `get_exchange_rate` | [frankfurter.app](https://frankfurter.app/) + Babel | Live local-currency → EUR rate |
| `get_transport` | OpenAI web search | Real journey time and ticket cost between cities |
| `geocode` | Open-Meteo geocoding | Coordinates, filtered by country |

**Weather is climate data, not a forecast.** Forecasts only reach ~16 days ahead
and these trips are months away, so the tool averages five years of real records
for that month and says so.

## Things learned the hard way

- **Never let the model count.** Asking for "exactly N days" produced 3 days for a
  6-day trip. The day-to-city allocation is now computed in Python and handed over
  as a fixed list.
- **Geocoding needs a country.** `"Galicia"` with `count=1` resolves to a village
  of 416 people in Chiapas, Mexico — which silently priced a Spanish holiday in
  Mexican pesos. The collector now insists on cities you sleep in, and records the
  country.
- **A model given no facts invents them fluently.** A prompt bug once sent the
  planner an empty context; it confidently produced a Paris itinerary for a
  traveller going to Serbia.

## Running it

### On Hugging Face Spaces

Set these under **Settings → Variables and secrets**:

| Secret | Purpose |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI key |
| `APP_PASSWORD` | Shared password — **required**, or strangers spend your credit |
| `APP_USERNAME` | Optional, defaults to `traveller` |

### Locally

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export APP_PASSWORD=choose-something
python app.py
```

## Files

| File | What it is |
|---|---|
| `app.py` | Gradio UI |
| `travel_assistant.py` | All the logic: chat, tools, itinerary, images, costing |
| `TravelAssisstant.ipynb` | The original notebook this grew out of |
| `project-brief-ai-travel-advisor.md` | The assignment |
