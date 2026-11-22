"""
PaperLeaf Books Support: a Streamlit web page for Paige.

It uses the same ADK agent as `adk web` (root_agent in paperleaf_support_agent/agent.py).

Two passcodes (both come from Streamlit secrets):
  APP_PASSCODE    -> customer: opens a fresh chat, sees only their own chat.
  ADMIN_PASSCODE  -> admin: sees all saved chats and the open tickets.

Run it on your laptop with:  .venv/Scripts/streamlit run app.py
"""

import asyncio
import csv
import hmac
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

# This must be the first Streamlit command.
st.set_page_config(page_title="PaperLeaf Books Support", page_icon="🍃", layout="centered")

PROJECT_FOLDER = Path(__file__).resolve().parent
TICKETS_FILE = PROJECT_FOLDER / "tickets" / "tickets.csv"
CHATS_FILE = PROJECT_FOLDER / "chats" / "chats.csv"
CHAT_COLUMNS = ["time", "session_id", "role", "message"]
GREETING = "Hello, I'm Paige from PaperLeaf Books. How can I help you today?"
APP_NAME = "paperleaf_web"


# ---------- Settings ----------
def get_secret(name):
    """Read a value from Streamlit secrets (empty text if it is not there)."""
    try:
        return str(st.secrets[name])
    except Exception:
        return ""


# When deployed, the key and model name come from Streamlit secrets. On your laptop they are not in
# secrets, so the agent reads them from the .env file instead.
for setting in ("GOOGLE_API_KEY", "GEMINI_MODEL"):
    if get_secret(setting):
        os.environ[setting] = get_secret(setting)


# ---------- Look and feel ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Lora:wght@600;700&display=swap');
    html, body, [class*="css"], .stMarkdown, .stTextInput, .stChatInput { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Lora', Georgia, serif !important; color: #1F2A24; }
    [data-testid="stHeader"] { background: transparent; }
    /* Chat bubbles: customer in green, Paige in white. */
    [data-testid="stChatMessage"] { border-radius: 16px; padding: 0.8rem 1rem; margin-bottom: 0.6rem;
        background: #FFFFFF; border: 1px solid #E3E8E0; }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: #2F6B4F; border-color: #2F6B4F; }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) * { color: #FFFFFF !important; }
    .stButton > button { border-radius: 10px; background: #2F6B4F; color: white; border: 0; }
    .stButton > button:hover { background: #245540; color: white; }
    .ticket-card { background: #FFFFFF; border: 1px solid #E3E8E0; border-left: 4px solid #2F6B4F;
        border-radius: 8px; padding: 0.5rem 0.7rem; margin-bottom: 0.5rem; font-size: 0.85rem; }
    .ticket-card.high { border-left-color: #C0392B; }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_logo():
    st.image(str(PROJECT_FOLDER / "assets" / "logo.svg"), width=260)


# ---------- The agent ----------
@st.cache_resource(show_spinner="Getting Paige ready...")
def get_backend():
    """Load Paige once. ADK is asynchronous, so it runs in its own background thread."""
    from google.adk.runners import InMemoryRunner

    from paperleaf_support_agent.agent import root_agent  # downloads the FAQ sheet

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop, InMemoryRunner(agent=root_agent, app_name=APP_NAME), root_agent.name


def run_async(coroutine):
    """Run an async ADK call and wait for its answer."""
    loop, _, _ = get_backend()
    return asyncio.run_coroutine_threadsafe(coroutine, loop).result()


async def start_chat(session_id):
    """Create a fresh ADK chat and record Paige's greeting in it, so she does not greet twice."""
    from google.adk.events import Event
    from google.genai import types

    _, runner, agent_name = get_backend()
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id="customer", session_id=session_id
    )
    greeting = types.Content(role="model", parts=[types.Part(text=GREETING)])
    await runner.session_service.append_event(session, Event(author=agent_name, content=greeting))


async def ask_paige(session_id, text):
    """Send the customer's message to Paige and return her reply."""
    from google.genai import types

    _, runner, _ = get_backend()
    message = types.Content(role="user", parts=[types.Part(text=text)])
    reply = []
    async for event in runner.run_async(user_id="customer", session_id=session_id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            reply += [part.text for part in event.content.parts if part.text]
    return " ".join(reply).strip()


# ---------- Saved chats and tickets ----------
def save_message(session_id, role, text):
    """Add one chat message to the end of chats/chats.csv (the admin reads this)."""
    CHATS_FILE.parent.mkdir(exist_ok=True)
    is_new_file = not CHATS_FILE.exists()
    with open(CHATS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(CHAT_COLUMNS)
        writer.writerow([datetime.now().isoformat(timespec="seconds"), session_id, role, text])


def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def show_open_tickets():
    st.sidebar.subheader("Open tickets")
    open_tickets = [t for t in read_csv(TICKETS_FILE) if t.get("status") == "open"]
    if not open_tickets:
        st.sidebar.caption("No open tickets.")
    for ticket in reversed(open_tickets):  # newest first
        css = "ticket-card high" if ticket["priority"] == "high" else "ticket-card"
        st.sidebar.markdown(
            f"<div class='{css}'><b>{ticket['ticket_id']}</b> · {ticket['priority']}<br>"
            f"{ticket['reason']}<br><small>{ticket['time']}</small></div>",
            unsafe_allow_html=True,
        )


# ---------- Pages ----------
def login_page():
    show_logo()
    st.title("PaperLeaf Books Support")
    customer_passcode = get_secret("APP_PASSCODE")
    admin_passcode = get_secret("ADMIN_PASSCODE")
    if not customer_passcode:
        st.error("The customer passcode is not set. Add APP_PASSCODE to the Streamlit secrets.")
        return
    with st.form("login"):
        entered = st.text_input("Passcode", type="password")
        submitted = st.form_submit_button("Open chat")
    if not submitted:
        return
    if admin_passcode and hmac.compare_digest(entered, admin_passcode):
        st.session_state.role = "admin"
        st.rerun()
    elif hmac.compare_digest(entered, customer_passcode):
        # Every customer login starts a brand-new chat.
        st.session_state.role = "customer"
        st.session_state.session_id = uuid.uuid4().hex
        st.session_state.messages = [{"role": "assistant", "text": GREETING}]
        run_async(start_chat(st.session_state.session_id))
        save_message(st.session_state.session_id, "assistant", GREETING)
        st.rerun()
    else:
        st.error("That passcode is not right. Please try again.")


def customer_page():
    show_logo()
    st.title("PaperLeaf Books Support")
    if st.sidebar.button("Start a new chat"):
        st.session_state.role = None
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🍃" if message["role"] == "assistant" else "🙂"):
            st.markdown(message["text"])

    prompt = st.chat_input("Type your message here...")
    if not prompt:
        return
    session_id = st.session_state.session_id
    st.session_state.messages.append({"role": "user", "text": prompt})
    save_message(session_id, "user", prompt)
    with st.chat_message("user", avatar="🙂"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🍃"):
        with st.spinner("Paige is typing..."):
            try:
                reply = run_async(ask_paige(session_id, prompt)) or "Sorry, I could not answer that. Please try again."
            except Exception:
                reply = "Sorry, something went wrong on our side. Please try again in a minute."
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "text": reply})
    save_message(session_id, "assistant", reply)


def admin_page():
    show_logo()
    st.title("Admin: all chats")
    if st.sidebar.button("Log out"):
        st.session_state.role = None
        st.rerun()
    show_open_tickets()

    # Group the saved messages by chat, newest chat first.
    chats = {}
    for row in read_csv(CHATS_FILE):
        chats.setdefault(row["session_id"], []).append(row)
    if not chats:
        st.info("No chats yet.")
    for session_id, rows in reversed(list(chats.items())):
        first_question = next((r["message"] for r in rows if r["role"] == "user"), "(no questions yet)")
        with st.expander(f"{rows[0]['time']} · {first_question[:60]}"):
            for row in rows:
                who = "Paige" if row["role"] == "assistant" else "Customer"
                st.markdown(f"**{who}:** {row['message']}")


# ---------- Start ----------
try:
    get_backend()
except Exception as error:
    st.error(f"Paige could not start: {error}")
    st.stop()

role = st.session_state.get("role")
if role == "admin":
    admin_page()
elif role == "customer":
    customer_page()
else:
    login_page()
