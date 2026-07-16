"""Trip-planning logic, lifted out of TravelAssisstant.ipynb so a web app can call it.

Differences from the notebook, all forced by having many users share one process:
  * no input() loop - the caller owns the conversation
  * no module-level USAGE - every function takes a `usage` list, one per session
  * images are returned as file paths in a temp dir, not written next to the code
"""
import base64
import json
import os
import tempfile
from pathlib import Path

import requests
from babel.numbers import get_territory_currencies
from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY from the environment

# --- which model does which job ------------------------------------------
CHAT_MODEL = "gpt-3.5-turbo"     # cheap: runs the conversation
PLANNER_MODEL = "gpt-4o"         # strong: itinerary, JSON, web search
IMAGE_MODEL = "gpt-image-1"
IMAGE_QUALITY = "medium"         # hero poster
DAY_IMAGE_QUALITY = "low"        # small per-day images

# USD per 1M tokens. https://openai.com/api/pricing/
PRICES = {
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-4o":        {"input": 2.50, "output": 10.00},
    "gpt-image-1":   {"input": 5.00, "output": 40.00},
}

MONTH_NUM = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

CLIMATE_YEARS = (2021, 2025)

STYLE = ("Vintage travel poster illustration, flat shapes, warm limited palette, "
         "clean composition. No text, no lettering, no words, no captions anywhere.")

COLLECTOR_SYSTEM = """
You are a friendly travel assistant. Your ONLY job in this conversation is to
collect information. You do NOT write the itinerary - another step does that.

Greet the traveler warmly, then collect, in this order:
1. Destination, number of days, and the month.
2. Main interests (food, museums, hiking, beaches, nightlife, shopping...).
3. Constraints: mobility, allergies, diet, travelling with kids, etc.

Rules:
- Ask about ONE topic per message, and keep messages short and friendly.
- Never ask a question they have already answered. Move on.
- If an answer is ambiguous or contradicts something earlier, ask one
  clarifying question before continuing.
- The trip must be organised around CITIES OR TOWNS the traveler sleeps in, never
  regions, provinces or countries. If they name a region or country ("Galicia",
  "Tuscany", "Japan"), say it is a big area and ask which one or two cities they
  want to use as bases, then split the nights between those cities.
- If they name more than one city, ask how many nights in each and how they plan
  to travel between them.
- If the nights per city do not sum to the stated trip length, ask which is
  correct before recapping. Do not silently pick one.
- If the traveler is unsure or asks for suggestions, reassure them briefly
  ("no worries - here's what most people love in <destination>"), then offer
  3 or 4 concrete options for that destination and let them pick. Never record a
  topic as "not specified".
- Once you have all three topics, stop asking. Output RECAP: followed by a
  single-line JSON object with keys destination, country (the English name of the
  country the cities are in, e.g. "Spain"), days (integer - total trip length),
  nights_per_city (object mapping each CITY OR TOWN -> number of nights),
  inter_city_transport (string, e.g. "car", "train"), month, interests,
  constraints.
  Then the word READY on its own line, and nothing after it.
"""

PLANNER_SYSTEM = """You are an expert travel planner. You write
complete, realistic, day-by-day itineraries. You never ask questions - you have
all the information you need. Output the full itinerary in one message."""


# --------------------------------------------------------------------------
# model calls
# --------------------------------------------------------------------------
def complete(messages, usage, model=CHAT_MODEL, temperature=0):
    r = client.chat.completions.create(model=model, messages=messages,
                                       temperature=temperature)
    usage.append({"model": model, "input": r.usage.prompt_tokens,
                  "output": r.usage.completion_tokens})
    return r.choices[0].message.content


def web_search(query, usage, model=PLANNER_MODEL):
    r = client.responses.create(model=model, tools=[{"type": "web_search"}],
                                input=query)
    usage.append({"model": model, "input": r.usage.input_tokens,
                  "output": r.usage.output_tokens})
    return r.output_text.strip()


def new_context():
    return [{"role": "system", "content": COLLECTOR_SYSTEM}]


def chat_turn(context, user_message, usage):
    """One turn of the collector conversation. Returns (reply, is_ready)."""
    context.append({"role": "user", "content": user_message})
    reply = complete(context, usage, model=CHAT_MODEL, temperature=0)
    context.append({"role": "assistant", "content": reply})
    return reply, "RECAP:" in reply


def parse_recap(reply):
    """Pull the RECAP JSON out of a collector reply. Tolerates ``` fences."""
    if "RECAP:" not in reply:
        raise ValueError("No RECAP: in that reply yet.")
    tail = reply.split("RECAP:", 1)[1]
    start = tail.find("{")
    if start == -1:
        raise ValueError("Found RECAP: but no JSON object after it.")
    recap, _ = json.JSONDecoder().raw_decode(tail[start:])
    return recap


# --------------------------------------------------------------------------
# tools: real data, no API keys
# --------------------------------------------------------------------------
def geocode(city, country=None):
    """`country` matters: "Galicia" alone resolves to a village in Mexico."""
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": 10}, timeout=20)
    r.raise_for_status()
    hits = r.json().get("results") or []
    if not hits:
        raise ValueError(f"could not geocode {city!r}")
    if country:
        want = country.strip().lower()
        in_country = [h for h in hits
                      if (h.get("country") or "").lower() == want
                      or (h.get("country_code") or "").lower() == want]
        if not in_country:
            found = ", ".join(sorted({h.get("country") or "?" for h in hits}))
            raise ValueError(f"{city!r} was not found in {country!r} "
                             f"(only in: {found}). Is it a region rather than a city?")
        hits = in_country
    hits.sort(key=lambda h: h.get("population") or 0, reverse=True)
    h = hits[0]
    return {"name": h["name"], "lat": h["latitude"], "lon": h["longitude"],
            "country": h.get("country"), "country_code": h.get("country_code")}


def get_weather(city, month, country=None):
    """Climate averages for `month`, from real daily records. Not a forecast."""
    mnum = MONTH_NUM[month.strip().lower()]
    loc = geocode(city, country)
    y0, y1 = CLIMATE_YEARS
    r = requests.get("https://archive-api.open-meteo.com/v1/archive",
                     params={"latitude": loc["lat"], "longitude": loc["lon"],
                             "start_date": f"{y0}-01-01", "end_date": f"{y1}-12-31",
                             "daily": "temperature_2m_max,temperature_2m_min,"
                                      "precipitation_sum",
                             "timezone": "auto"}, timeout=60)
    r.raise_for_status()
    d = r.json()["daily"]
    rows = [(mx, mn, pr) for t, mx, mn, pr in zip(
        d["time"], d["temperature_2m_max"], d["temperature_2m_min"],
        d["precipitation_sum"])
        if int(t[5:7]) == mnum and None not in (mx, mn, pr)]
    if not rows:
        raise ValueError(f"no archive data for {city} in {month}")
    return {"city": loc["name"], "month": month,
            "avg_high_c": round(sum(x[0] for x in rows) / len(rows), 1),
            "avg_low_c": round(sum(x[1] for x in rows) / len(rows), 1),
            "rainy_days_in_month": round(
                sum(1 for x in rows if x[2] >= 1.0) / (y1 - y0 + 1), 1),
            "source": f"Open-Meteo archive, {y0}-{y1} average"}


def get_exchange_rate(country_code):
    codes = get_territory_currencies(country_code)
    if not codes:
        return {"error": f"no currency known for {country_code}"}
    cur = codes[0]
    if cur == "EUR":
        return {"currency": "EUR", "eur_per_unit": 1.0,
                "note": "destination already uses EUR, no conversion needed"}
    r = requests.get("https://api.frankfurter.app/latest",
                     params={"from": cur, "to": "EUR"}, timeout=20)
    if r.status_code != 200 or "EUR" not in r.json().get("rates", {}):
        return {"currency": cur, "eur_per_unit": None,
                "note": f"frankfurter has no EUR rate for {cur}"}
    j = r.json()
    return {"currency": cur, "eur_per_unit": j["rates"]["EUR"], "as_of": j["date"]}


def get_transport(city_a, city_b, mode, usage):
    if mode.strip().lower() in ("car", "drive", "driving"):
        q = (f"How far is it to drive from {city_a} to {city_b}, how long does the "
             f"drive take, and are there tolls? Answer in two sentences.")
    else:
        q = (f"How long does the {mode} journey from {city_a} to {city_b} take door "
             f"to door, and roughly what does a one-way ticket cost? "
             f"Answer in two sentences.")
    return web_search(q, usage)


def gather_facts(recap, usage):
    cities = list(recap["nights_per_city"])
    ctry = recap.get("country")
    facts = {"weather": {}, "currency": None, "transport": None}

    for c in cities:
        try:
            facts["weather"][c] = get_weather(c, recap["month"], ctry)
        except Exception as e:
            facts["weather"][c] = {"error": f"{type(e).__name__}: {e}"}
    try:
        facts["currency"] = get_exchange_rate(geocode(cities[0], ctry)["country_code"])
    except Exception as e:
        facts["currency"] = {"error": f"{type(e).__name__}: {e}"}
    if len(cities) > 1:
        try:
            facts["transport"] = get_transport(cities[0], cities[1],
                                               recap["inter_city_transport"], usage)
        except Exception as e:
            facts["transport"] = {"error": f"{type(e).__name__}: {e}"}
    return facts


# --------------------------------------------------------------------------
# itinerary
# --------------------------------------------------------------------------
def build_day_plan(recap):
    """Which city each day belongs to. Python decides this, not the model."""
    plan = []
    for city, n in recap["nights_per_city"].items():
        plan.extend([city] * n)
    return plan


def build_itinerary(recap, facts, usage):
    n_days = recap["days"]
    nights = recap["nights_per_city"]
    day_plan = build_day_plan(recap)
    day_plan_text = "\n".join(f"Day {i}: {c}" for i, c in enumerate(day_plan, 1))

    prompt = f"""Write a travel itinerary for this traveler:

{json.dumps(recap, indent=2)}

Real external data retrieved for this trip (weather from historical records,
exchange rate live today, transport from a web search). Treat it as fact and
never contradict it:

{json.dumps(facts, indent=2, ensure_ascii=False)}

Day-to-city allocation. This is fixed and already decided - follow it EXACTLY,
writing one ### Day block per line below, in this order:

{day_plan_text}

Rules:
- Start with a trip title (# heading) and a two-line trip summary.
- Output exactly {n_days} ### Day blocks, matching the allocation above. Do not
  re-balance it, shorten it or extend it.
- The first day in a new city is the travel day: the inter-city journey occupies
  a named block on it, using the real duration from the retrieved transport data
  (e.g. "Morning: train London-Oxford, ~1h").
- The traveler travels between cities by {recap['inter_city_transport']}. Use that
  mode, never another.
- The <city> in the day header must be the single city named in the allocation
  above. Never "A to B".
- Never place activities in two cities on the same day.
- Activities within one day must be geographically coherent. Anything more than
  ~45 min from the city must take the whole day, not a morning slot.
- Use the retrieved weather when planning. If the month is cold or wet, favour
  indoor activities and warn about it; if mild, favour outdoor ones. Do not
  invent temperatures - only use the figures given above.
- Only name a restaurant, venue or park you are confident actually exists. If
  unsure, describe the type of place and the street/area instead of inventing a
  name. Never invent a plausible-sounding name, and never turn a local dish into
  a restaurant name.
- Every day block must contain all five lines. Never omit a line.

Format each day exactly like this:

### Day N - <city> - <theme>
- Morning: <activity>
- Lunch: <restaurant>, <neighbourhood> - <why it fits their preferences>
- Afternoon: <activity>
- Dinner: <restaurant>, <neighbourhood> - <why it fits>
- Evening: <activity or "free">

Output the day blocks back to back, with nothing in between them. Do NOT put
accommodation, budget or tips inside a day block.

AFTER the final day block, output these four sections ONCE for the whole trip.
Each section heading must be a ### heading - the SAME markdown level as the day
headings above - with the emoji shown at both the start and the end. Copy these
four headings exactly, character for character, emoji included:

### 🏨 Accommodation 🏨
Exactly {len(nights)} lines - one per city, in this format:
<district>, <city> - <why it suits this traveler>

Hard requirements for <district>:
- It must be the PROPER NAME of a real barrio/neighbourhood of that city, the
  name a local would use and a name that appears on a map of that city.
  Good: "Juderia, Segovia". Bad: "Segovia Old Town, Segovia".
- It is FORBIDDEN to use a generic description instead of a name. Reject:
  "centre", "city centre", "city center", "old town", "old quarter",
  "historic centre", "casco antiguo", "downtown", and any translation or
  variation of these. A district name is a proper noun, not a description.
- The district must lie INSIDE the city it is listed under - never a separate
  nearby town or municipality.
- If you are not confident that you know a real barrio name for that city, do
  NOT guess and do NOT fall back on a generic phrase. Instead name a specific
  street or landmark to stay beside, e.g. "beside the Aqueduct, Calle Cervantes".
- The district must not change while the traveler is in the same city.

### 🌦️ Weather 🌦️
One line per city, quoting the retrieved figures exactly:
<city>: typical <month> high <X>C / low <Y>C, about <Z> rainy days that month.

### 💰 Estimated budget 💰
Estimate it yourself from typical mid-range prices for {recap['month']}. Never
ask the traveler for a budget. Use the local currency named in the retrieved
currency data, on every line. Output exactly these five lines, replacing CUR
with that currency code:
- Lodging: CUR X-Y
- Food: CUR X-Y
- Activities: CUR X-Y
- Transport: CUR X-Y
- **Total: CUR X-Y**
All figures per person, for the WHOLE TRIP - not per day, not per night. Use
whole numbers only. The total must be the sum of the four lines above - add them
up and check before writing.
Then, ONLY if the retrieved currency is not EUR and eur_per_unit is not null,
add one more line converting the total using that exact rate, rounded to whole
euros:
- **Total in EUR: EUR X-Y** (at 1 CUR = <eur_per_unit> EUR, <as_of>)

### 💡 Practical tips 💡
3-5 bullets. At least one must be about what to pack for the weather above.
"""
    return complete([{"role": "system", "content": PLANNER_SYSTEM},
                     {"role": "user", "content": prompt}],
                    usage, model=PLANNER_MODEL, temperature=0.7)


SUMMARY_PROMPT = """Convert the itinerary you just wrote into JSON.

Copy the details exactly as written above - do not invent, re-plan, or omit
anything. If a field is missing from the itinerary, use null.

Return only the JSON object, with this shape:
{
  "trip_title": str, "trip_summary": str, "accommodation": str,
  "days": [ {"day": int, "city": str, "theme": str,
             "eat": {"lunch": str, "dinner": str},
             "do": [str]} ],
  "tips": [str],
  "estimated_budget": {"lodging": str, "food": str,
                       "activities": str, "transport": str, "total": str}
}
"""


def summarise(itinerary, usage):
    raw = complete([{"role": "user", "content": itinerary + "\n\n" + SUMMARY_PROMPT}],
                   usage, model=PLANNER_MODEL, temperature=0)
    start = raw.find("{")
    if start == -1:
        raise ValueError("No JSON object in the summary reply:\n" + raw)
    data, _ = json.JSONDecoder().raw_decode(raw[start:])
    return data


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------
def _interests_text(recap):
    i = recap.get("interests")
    return ", ".join(i) if isinstance(i, list) else str(i)


def hero_image_prompt(recap):
    cities = list(recap["nights_per_city"])
    return (f"{STYLE} Subject: a single poster for one trip visiting "
            f"{' and '.join(cities)}, {recap.get('country', '')} in "
            f"{recap['month']}. Combine their most recognisable real landmarks "
            f"into one scene. Hint at these interests: {_interests_text(recap)}.")


def day_image_prompt(day, recap):
    activities = "; ".join(day.get("do") or [])[:280]
    return (f"{STYLE} One single clear scene, not a collage. "
            f"Subject: {day.get('theme')} in {day.get('city')}, "
            f"{recap.get('country', '')}, in {recap['month']}. "
            f"Depict this day's activities: {activities}")


def generate_image(prompt, out_dir, filename, usage, quality):
    r = client.images.generate(model=IMAGE_MODEL, prompt=prompt, size="1024x1024",
                               quality=quality, n=1)
    usage.append({"model": IMAGE_MODEL, "input": r.usage.input_tokens,
                  "output": r.usage.output_tokens})
    path = Path(out_dir) / filename
    path.write_bytes(base64.b64decode(r.data[0].b64_json))
    return str(path)


def make_images(recap, summary_data, usage, out_dir=None, progress=None):
    """Hero poster + one image per day. Returns (hero_path, [(path, caption)])."""
    out_dir = out_dir or tempfile.mkdtemp(prefix="trip_")
    if progress:
        progress("Painting the trip poster...")
    hero = generate_image(hero_image_prompt(recap), out_dir, "00_hero.png",
                          usage, IMAGE_QUALITY)

    gallery = []
    days = summary_data.get("days") or []
    for d in days:
        if progress:
            progress(f"Painting day {d['day']} of {len(days)}...")
        p = generate_image(day_image_prompt(d, recap), out_dir,
                           f"day_{d['day']:02d}.png", usage, DAY_IMAGE_QUALITY)
        gallery.append((p, f"Day {d['day']} - {d.get('city')} - {d.get('theme')}"))
    return hero, gallery


# --------------------------------------------------------------------------
# cost
# --------------------------------------------------------------------------
EUR_PER_USD = 0.92


def usage_report_md(usage):
    if not usage:
        return "_No API calls yet._"
    by_model = {}
    for rec in usage:
        m = by_model.setdefault(rec["model"], {"calls": 0, "input": 0, "output": 0})
        m["calls"] += 1
        m["input"] += rec["input"]
        m["output"] += rec["output"]

    rows, total = [], 0.0
    for model, m in by_model.items():
        price = PRICES.get(model)
        if price is None:
            cost_s = "n/a"
        else:
            cost = (m["input"] / 1e6 * price["input"]
                    + m["output"] / 1e6 * price["output"])
            total += cost
            cost_s = f"${cost:.4f}"
        rows.append(f"| `{model}` | {m['calls']} | {m['input']:,} | "
                    f"{m['output']:,} | {cost_s} |")

    tin = sum(m["input"] for m in by_model.values())
    tout = sum(m["output"] for m in by_model.values())
    return (
        "| model | calls | input | output | cost |\n"
        "|---|---:|---:|---:|---:|\n"
        + "\n".join(rows)
        + f"\n| **TOTAL** | **{len(usage)}** | **{tin:,}** | **{tout:,}** | "
          f"**${total:.4f}** |\n\n"
        + f"**{tin + tout:,} tokens — ${total:.4f} (≈ €{total * EUR_PER_USD:.4f})**"
    )
