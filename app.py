"""Gradio front end for the AI Travel Advisor. Runs on Hugging Face Spaces.

Secrets needed (Space settings -> Variables and secrets):
    OPENAI_API_KEY   your OpenAI key
    APP_PASSWORD     shared password; without it nobody can spend your credit
    APP_USERNAME     optional, defaults to "traveller"
"""
import os
from pathlib import Path

import gradio as gr

# Local runs only: load .env.local if present. On Spaces the secrets are already
# in the environment and this file does not exist.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env.local")
except ImportError:
    pass

import travel_assistant as ta

INTRO = """# 🌍 AI Travel Advisor

Tell me where you want to go. I'll ask a few questions, then plan the trip
against **real data** — historical weather, live exchange rates, and a web
search for the journey between cities.
"""

GREETING = ("Hello! Where are you thinking of travelling to, for how many days, "
            "and in which month?")


def new_state():
    return ta.new_context(), []          # context, usage


def on_send(message, chat, context, usage):
    """One conversation turn with the cheap model."""
    message = (message or "").strip()
    if not message:
        return chat, context, usage, gr.skip(), ""

    try:
        reply, ready = ta.chat_turn(context, message, usage)
    except Exception as e:
        chat = chat + [{"role": "user", "content": message},
                       {"role": "assistant", "content": f"⚠️ {type(e).__name__}: {e}"}]
        return chat, context, usage, gr.update(), ""

    # Hide the machine-readable RECAP block from the human.
    shown = reply.split("RECAP:")[0].strip() if ready else reply
    if ready and not shown:
        shown = "Got everything I need. Hit **Plan my trip** below. ✅"

    chat = chat + [{"role": "user", "content": message},
                   {"role": "assistant", "content": shown}]
    return chat, context, usage, gr.update(interactive=ready, variant="primary"), ""


def on_plan(context, usage, progress=gr.Progress()):
    """Everything after READY: tools, itinerary, JSON, images, cost."""
    print("[plan] starting", flush=True)  # shows up in the Space logs
    last = next((m["content"] for m in reversed(context)
                 if m["role"] == "assistant" and "RECAP:" in m["content"]), None)
    if last is None:
        raise gr.Error("No trip collected yet — finish the chat first.")

    recap = ta.parse_recap(last)

    progress(0.1, desc="Looking up weather, currency and transport...")
    facts = ta.gather_facts(recap, usage)

    progress(0.35, desc="Planning your days...")
    itinerary = ta.build_itinerary(recap, facts, usage)

    progress(0.5, desc="Structuring the plan...")
    summary = ta.summarise(itinerary, usage)

    progress(0.6, desc="Painting pictures (this is the slow bit)...")
    hero, gallery = ta.make_images(recap, summary, usage,
                                   progress=lambda m: progress(0.7, desc=m))

    header = f"# {summary['trip_title']}\n\n*{summary['trip_summary']}*"
    body = itinerary[itinerary.find("### Day"):] if "### Day" in itinerary else itinerary

    return (gr.update(visible=True), header, hero, body, gallery,
            ta.usage_report_md(usage))


with gr.Blocks(title="AI Travel Advisor") as demo:
    context_st = gr.State(ta.new_context)
    usage_st = gr.State(list)

    gr.Markdown(INTRO)

    with gr.Row():
        with gr.Column(scale=1):
            chat = gr.Chatbot(
                height=430, label="Planning chat",
                value=[{"role": "assistant", "content": GREETING}],
            )
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="e.g. London and Oxford, 5 days in September",
                    show_label=False, scale=5, autofocus=True,
                )
                send_btn = gr.Button("Send", scale=1)
            plan_btn = gr.Button("Plan my trip 🧳", interactive=False)
            gr.Markdown("<sub>The button turns on once I have enough to plan.</sub>")

        with gr.Column(scale=1, visible=False) as results:
            title_md = gr.Markdown()
            hero_img = gr.Image(height=340, show_label=False)
            itinerary_md = gr.Markdown()
            gallery = gr.Gallery(label="Day by day", columns=3, height=260)
            gr.Markdown("### 🧾 Token usage and cost")
            usage_md = gr.Markdown()

    send_inputs = [msg, chat, context_st, usage_st]
    send_outputs = [chat, context_st, usage_st, plan_btn, msg]
    msg.submit(on_send, send_inputs, send_outputs)
    send_btn.click(on_send, send_inputs, send_outputs)

    plan_btn.click(on_plan, [context_st, usage_st],
                   [results, title_md, hero_img, itinerary_md, gallery, usage_md])


if __name__ == "__main__":
    password = os.environ.get("APP_PASSWORD")
    username = os.environ.get("APP_USERNAME", "traveller")
    if not password:
        # Fail loudly: a public Space with no gate spends real money for strangers.
        raise SystemExit(
            "APP_PASSWORD is not set. Set it as a Space secret (or export it "
            "locally) before starting — otherwise anyone who finds this app can "
            "spend your OpenAI credit."
        )
    demo.launch(auth=(username, password),
                auth_message="Ask Casilda for the password.",
                theme=gr.themes.Soft())
