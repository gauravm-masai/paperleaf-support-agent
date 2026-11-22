"""
PaperLeaf Books Support: a Streamlit web page for Paige.

It uses the same ADK agent as `adk web` (root_agent in paperleaf_support_agent/agent.py).
The look follows STYLEGUIDE.md.

Two passcodes (both come from Streamlit secrets):
  APP_PASSCODE    -> customer: opens a fresh chat, sees only their own chat.
  ADMIN_PASSCODE  -> admin: sees all saved chats and the open tickets.

Run it on your laptop with:  .venv/Scripts/streamlit run app.py
"""

import asyncio
import csv
import hmac
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

# This must be the first Streamlit command.
st.set_page_config(page_title="PaperLeaf Books Support", page_icon="🍃", layout="wide")

PROJECT_FOLDER = Path(__file__).resolve().parent
LOGO_FILE = str(PROJECT_FOLDER / "assets" / "logo.svg")
TICKETS_FILE = PROJECT_FOLDER / "tickets" / "tickets.csv"
CHATS_FILE = PROJECT_FOLDER / "chats" / "chats.csv"
CHAT_COLUMNS = ["time", "session_id", "role", "message"]
FEEDBACK_FILE = PROJECT_FOLDER / "feedback" / "feedback.csv"
FEEDBACK_COLUMNS = ["time", "session_id", "question", "reply", "helpful"]
GREETING = "Hello, I'm Paige from PaperLeaf Books. How can I help you today?"
APP_NAME = "paperleaf_web"

# The suggested questions in the chat page's left sidebar. Clicking one sends it to Paige as written.
SUGGESTED_QUESTIONS = [
    "How much does delivery cost?",
    "What is your return policy?",
    "How do I track my order?",
]

# The three cards on the homepage: (label, icon, the question Paige is asked when the card is used).
HOME_CARDS = [
    ("Track an order", ":material/package_2:", "How do I track my order?"),
    ("Start a return", ":material/autorenew:", "How do I return an item?"),
    ("Delivery costs", ":material/local_shipping:", "How much does delivery cost?"),
]

# A small leaf picture (used as Paige's avatar and in the homepage preview).
LEAF_URL = (
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 80'>"
    "<path d='M40 8C14 14 8 44 22 62 24 50 30 40 46 30 36 42 32 54 34 66 56 60 70 34 40 8Z' fill='%231B5A45'/></svg>"
)


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


# ---------- Look and feel (see STYLEGUIDE.md) ----------
STYLE = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');
:root { --page: #F5F3EC; --card: #FFFFFF; --ink: #12251C; --green: #1B5A45; --green-deep: #144636;
        --pale: #DDEBE1; --tint: #E8F0EA; --line: #D9DFD9; --outline: #33433A; --muted: #5F6F66; --alert: #C0392B;
        --shadow: 0 6px 24px rgba(18, 37, 28, 0.08); }

html, body, [class*="css"], .stMarkdown, .stTextInput, .stChatInput { font-family: 'Inter', sans-serif; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none; }
[data-testid="stMain"] { overflow-x: hidden; }

/* Headlines: an elegant serif (Fraunces). */
h1 { font-family: 'Fraunces', Georgia, serif !important; font-weight: 600 !important; letter-spacing: -0.03em;
     font-size: 2rem !important; line-height: 1.1 !important; color: var(--ink); padding: 0 0 1.2rem 0 !important; }
h2, h3 { font-family: 'Fraunces', Georgia, serif !important; font-weight: 600 !important; letter-spacing: -0.02em; }
[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--line); }

/* ----- Homepage ----- */
.st-key-nav { background: var(--card); width: 100vw !important; max-width: none !important; box-sizing: border-box;
    margin: -2rem 0 2.2rem calc(50% - 50vw) !important; padding: 0.7rem calc(50vw - 50%) !important; }
.st-key-nav [data-testid="stColumn"]:last-child [data-testid="stElementContainer"],
.st-key-nav [data-testid="stColumn"]:last-child [data-testid="stButton"] { display: flex; justify-content: flex-end; width: 100%; }
.st-key-nav [data-testid="stButton"] button { border: 0; background: transparent; color: var(--ink);
    white-space: nowrap; width: auto; }
.st-key-nav [data-testid="stButton"] button p { font-weight: 600; font-size: 1.1rem; overflow: visible; text-overflow: clip; }
.st-key-nav [data-testid="stButton"] button:hover { background: var(--tint); }
.hero-title { font-family: 'Fraunces', Georgia, serif; font-weight: 500; color: var(--ink);
    font-size: clamp(2.8rem, 5.2vw, 4.7rem); line-height: 0.98; letter-spacing: -0.035em; margin: 0 0 1.2rem 0; }
[data-testid="stMarkdownContainer"] p.hero-sub { color: var(--ink); font-size: 1.3rem; margin: 0 0 1.6rem 0; }
.st-key-cta button { background: var(--green); color: #FFFFFF; border: 0; border-radius: 12px; padding: 0.85rem 1.8rem; }
.st-key-cta button p { font-weight: 600; font-size: 1.2rem; }
.st-key-cta button:hover { background: var(--green-deep); color: #FFFFFF; }

/* The sample chat in the hero panel. */
.hero-panel { position: relative; background: var(--pale); border-radius: 28px; padding: 3rem 2.2rem; }
.hero-sheet { position: absolute; background: #CFE2D5; border-radius: 14px; }
.hero-sheet-a { width: 42%; height: 62%; right: 6%; top: 8%; transform: rotate(8deg); }
.hero-sheet-b { width: 40%; height: 50%; left: 4%; bottom: 8%; transform: rotate(-8deg); }
.hero-card { position: relative; background: var(--card); border-radius: 20px; padding: 1.2rem 1.4rem 1.4rem;
    box-shadow: var(--shadow); }
.hero-card-head { display: flex; align-items: center; gap: 0.6rem; font-weight: 600; padding-bottom: 0.9rem;
    border-bottom: 1px solid var(--line); margin-bottom: 1rem; }
.hero-leaf, .hero-avatar { flex: none; width: 30px; height: 30px; border-radius: 50%;
    background: var(--pale) url("LEAF_URL") center / 55% no-repeat; }
.hero-row { display: flex; align-items: flex-start; gap: 0.6rem; margin-bottom: 0.8rem; }
.hero-row.user { justify-content: flex-end; }
.hero-bubble { padding: 0.65rem 1rem; border-radius: 18px; font-size: 0.95rem; line-height: 1.4; }
.hero-bubble.user { background: var(--green); color: #FFFFFF; border-bottom-right-radius: 5px; }
.hero-bubble.paige { background: var(--tint); color: var(--ink); border-top-left-radius: 5px; }

/* The three cards under the hero. */
.st-key-cards button { background: var(--card); color: var(--ink); border: 1px solid var(--outline);
    border-radius: 14px; padding: 1.25rem 1.4rem; font-weight: 600; display: flex;
    align-items: center; justify-content: space-between; }
.st-key-cards button > div { display: flex; align-items: center; justify-content: flex-start; gap: 0.9rem; flex: 1; }
.st-key-cards button > div * { justify-content: flex-start; text-align: left; }
.st-key-cards button p { font-size: 1.2rem; }
.st-key-cards button [data-testid="stIconMaterial"] { font-size: 1.5rem !important; width: 1.5rem; height: 1.5rem;
    margin-right: 0.9rem; }
.st-key-cards button::after { content: "\2192"; font-size: 1.5rem; }
.st-key-cards button:hover { background: var(--tint); color: var(--ink); border-color: var(--outline); }

/* Passcode card. */
[data-testid="stForm"] { background: var(--card); border: 1px solid var(--line); border-radius: 18px;
    padding: 1.3rem; box-shadow: var(--shadow); max-width: 420px; }
[data-testid="stFormSubmitButton"] button { background: var(--green); color: #FFFFFF; border: 0;
    border-radius: 12px; font-weight: 600; }
[data-testid="stFormSubmitButton"] button:hover { background: var(--green-deep); color: #FFFFFF; }

/* ----- Chat page ----- */
[data-testid="stSidebar"] [data-testid="stButton"] button { border-radius: 12px; font-weight: 600;
    background: var(--card); color: var(--green); border: 1px solid var(--green); }
[data-testid="stSidebar"] [data-testid="stButton"] button:hover { background: var(--tint); }

/* The sidebar fills the page height, so the "Start a new chat" / "Log out" button can sit at the very bottom. */
/* The negative top margin lifts the logo so it lines up with the page title beside it. */
.st-key-sidebar_body { min-height: calc(100vh - 3rem); margin-top: -3.1rem; }
.st-key-newchat { margin-top: auto; }

/* Chat bubbles. The customer is on the right in dark green; Paige is on the left in pale green with a leaf. */
[data-testid="stElementContainer"]:has(.bubble-marker) { display: none; }
[class*="st-key-user_"] { align-items: flex-end; margin-bottom: 0.9rem; }
[class*="st-key-user_"] [data-testid="stElementContainer"]:has(.bubble-marker) + [data-testid="stElementContainer"] {
    width: fit-content; max-width: 85%; background: var(--green); padding: 0.75rem 1.1rem;
    border-radius: 20px 20px 6px 20px; }
[class*="st-key-user_"] [data-testid="stMarkdownContainer"] p { color: #FFFFFF; margin: 0; }
[class*="st-key-paige_"] { flex-direction: row; align-items: flex-start; gap: 0.7rem; margin-bottom: 0.9rem; }
[class*="st-key-paige_"]::before { content: ""; flex: none; width: 36px; height: 36px; border-radius: 50%;
    background: var(--pale) url("LEAF_URL") center / 55% no-repeat; }
[class*="st-key-paige_"] [data-testid="stVerticalBlock"] { flex: 1; min-width: 0; max-width: 88%; gap: 0.3rem; }
[class*="st-key-paige_"] [data-testid="stElementContainer"]:has(.bubble-marker) + [data-testid="stElementContainer"] {
    width: fit-content; max-width: 100%; background: var(--pale); padding: 0.75rem 1.1rem;
    border-radius: 6px 20px 20px 20px; }
[class*="st-key-paige_"] [data-testid="stMarkdownContainer"] p { margin: 0; }
/* Streamlit gives markdown a negative bottom margin, which would clip the bubble; switch it off. */
[class*="st-key-user_"] [data-testid="stMarkdownContainer"],
[class*="st-key-paige_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }

/* Typing dots: three softly pulsing dots shown in Paige's bubble while she answers. */
.typing i { display: inline-block; width: 8px; height: 8px; margin: 0 3px; border-radius: 50%;
    background: var(--green); opacity: 0.3; animation: pulse 1.2s infinite ease-in-out; }
.typing i:nth-child(2) { animation-delay: 0.2s; }
.typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse { 0%, 80%, 100% { opacity: 0.3; transform: scale(0.85); } 40% { opacity: 1; transform: scale(1.1); } }

/* Subtle motion: new messages fade in, cards lift a little on hover. */
@keyframes fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
[class*="st-key-user_"], [class*="st-key-paige_"] { animation: fadein 0.3s ease; }
.st-key-cards button, .st-key-cta button { transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease; }
.st-key-cards button:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
.st-key-cta button:hover { transform: translateY(-2px); }

/* Info strip under the homepage cards. */
.info-strip { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.8rem 2rem; margin-top: 2.2rem;
    padding-top: 1.3rem; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.98rem; }
.info-strip span::before { content: "\2713"; color: var(--green); font-weight: 700; margin-right: 0.55rem; }
.info-strip b { color: var(--ink); font-weight: 600; }

/* The "Was this helpful?" row: the text and the thumbs sit together on the left, each only as wide as it needs. */
[class*="st-key-feedback_"] { justify-content: flex-start; align-items: center; }
[class*="st-key-feedback_"] > * { flex: 0 0 auto !important; width: auto !important; min-width: 0; }

/* Chat box. */
[data-testid="stChatInput"] { border-radius: 999px; border: 1px solid var(--line); background: var(--card);
    box-shadow: var(--shadow); }
[data-testid="stChatInput"]:focus-within { border-color: var(--green); }

/* Suggested questions: a plain, left-aligned list (not buttons). A soft tint appears on hover. */
.st-key-suggested [data-testid="stButton"] button { border: 0; background: transparent; color: var(--ink);
    font-weight: 400; border-radius: 14px; padding: 0.6rem 0.8rem; }
.st-key-suggested [data-testid="stButton"] button,
.st-key-suggested [data-testid="stButton"] button * { justify-content: flex-start !important; text-align: left !important; }
.st-key-suggested [data-testid="stButton"] button p { font-size: 1.05rem; line-height: 1.35; }
.st-key-suggested [data-testid="stButton"] button:hover { background: var(--tint); color: var(--ink); border: 0; }

/* Ticket cards in the sidebar. */
.ticket-card { background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--green);
    border-radius: 14px; padding: 0.7rem 0.9rem; margin-bottom: 0.7rem; font-size: 0.85rem; box-shadow: var(--shadow); }
.ticket-card small { color: var(--muted); }
.ticket-card.high { border-left-color: var(--alert); }
</style>
"""
st.markdown(STYLE.replace("LEAF_URL", LEAF_URL), unsafe_allow_html=True)


def page_width(max_width, top_padding, side_padding="5rem"):
    """Set how wide the page is, the space above the first thing on it, and the space at the sides."""
    st.markdown(
        f"<style>[data-testid='stMainBlockContainer'], [data-testid='stBottomBlockContainer'] "
        f"{{ max-width: {max_width}; padding-left: {side_padding}; padding-right: {side_padding}; }}"
        f"[data-testid='stMainBlockContainer'] {{ padding-top: {top_padding}; }}</style>",
        unsafe_allow_html=True,
    )


def bubble(text, html=False):
    """The message text. The hidden marker tells the style sheet to draw it as a chat bubble."""
    st.markdown("<span class='bubble-marker'></span>", unsafe_allow_html=True)
    st.markdown(text, unsafe_allow_html=html)


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
def append_row(path, columns, row):
    """Add one row to the end of a CSV file (the header is written first if the file is new)."""
    path.parent.mkdir(exist_ok=True)
    is_new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(columns)
        writer.writerow(row)


def save_message(session_id, role, text):
    """Add one chat message to the end of chats/chats.csv (the admin reads this)."""
    append_row(CHATS_FILE, CHAT_COLUMNS, [datetime.now().isoformat(timespec="seconds"), session_id, role, text])


def record_feedback(index):
    """Save a thumbs up/down click to feedback/feedback.csv, with the question and reply it is about."""
    answer = "Yes" if st.session_state[f"helpful_{index}"] == 1 else "No"  # thumbs up = 1, down = 0
    messages = st.session_state.messages
    append_row(
        FEEDBACK_FILE,
        FEEDBACK_COLUMNS,
        [
            datetime.now().isoformat(timespec="seconds"),
            st.session_state.session_id,
            messages[index - 1]["text"],  # the customer's question just before the reply
            messages[index]["text"],
            answer,
        ],
    )
    st.session_state.feedback[index] = answer


def show_feedback(index):
    """Under a reply: a small 'Was this helpful?' line with thumbs up/down icons (one answer per reply)."""
    given = st.session_state.feedback.get(index)
    # One compact row, on the left: the text with the thumbs right beside it.
    with st.container(key=f"feedback_{index}", horizontal=True, vertical_alignment="center", gap="small"):
        st.caption("Thanks for your feedback" if given else "Was this helpful?")
        # After an answer, the chosen thumb stays shown but can no longer be changed.
        st.feedback(
            "thumbs",
            key=f"helpful_{index}",
            disabled=given is not None,
            on_change=record_feedback,
            args=(index,),
        )


def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def show_open_tickets(only_ids=None):
    """Show open tickets in the sidebar. only_ids limits it to those ticket IDs (used for customers)."""
    st.subheader("Your tickets" if only_ids is not None else "Open tickets")
    open_tickets = [t for t in read_csv(TICKETS_FILE) if t.get("status") == "open"]
    if only_ids is not None:
        open_tickets = [t for t in open_tickets if t["ticket_id"] in only_ids]
    if not open_tickets:
        st.caption("No open tickets.")
    for ticket in reversed(open_tickets):  # newest first
        css = "ticket-card high" if ticket["priority"] == "high" else "ticket-card"
        st.markdown(
            f"<div class='{css}'><b>{ticket['ticket_id']}</b> · {ticket['priority']}<br>"
            f"{ticket['reason']}<br><small>{ticket['time']}</small></div>",
            unsafe_allow_html=True,
        )


# ---------- Pages ----------
# A sample chat shown in the homepage's right-hand panel (it matches a real answer from the FAQ).
HERO_PREVIEW = (
    "<div class='hero-panel'><div class='hero-sheet hero-sheet-a'></div><div class='hero-sheet hero-sheet-b'></div>"
    "<div class='hero-card'><div class='hero-card-head'><span class='hero-leaf'></span>PaperLeaf Support</div>"
    "<div class='hero-row user'><span class='hero-bubble user'>How much does delivery cost?</span></div>"
    "<div class='hero-row'><span class='hero-avatar'></span><span class='hero-bubble paige'>"
    "Delivery is free on orders above ₹499. Below that, a flat ₹49 fee applies.</span></div></div></div>"
)


def open_passcode(question=None):
    """Show the passcode card. If a card was clicked, remember its question to ask Paige after login."""
    st.session_state.show_passcode = True
    if question:
        st.session_state.pending_question = question


def leave_chat():
    """Go back to the homepage."""
    st.session_state.role = None
    st.session_state.show_passcode = False


def passcode_card():
    """The passcode box. The customer passcode opens a fresh chat; the admin passcode opens the admin page."""
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
        st.session_state.feedback = {}  # reply number -> "Yes" or "No"
        run_async(start_chat(st.session_state.session_id))
        save_message(st.session_state.session_id, "assistant", GREETING)
        # If the customer came in through a card, ask Paige that question straight away.
        pending = st.session_state.pop("pending_question", None)
        if pending:
            st.session_state.clicked_question = pending
        st.rerun()
    else:
        st.error("That passcode is not right. Please try again.")


def home_page():
    page_width("1180px", "0rem")
    # Top bar: logo on the left, "Get support" on the right.
    with st.container(key="nav"):
        logo_column, link_column = st.columns([4, 1], vertical_alignment="center")
        logo_column.image(LOGO_FILE, width=170)
        link_column.button("Get support", key="nav_support", on_click=open_passcode)

    # Hero: headline, one line of text and the start button on the left; a sample chat on the right.
    left, right = st.columns([1.05, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            "<div class='hero-title'>Get answers from PaperLeaf.</div>"
            "<p class='hero-sub'>Ask about orders, returns, or delivery.</p>",
            unsafe_allow_html=True,
        )
        st.button("Start a conversation  →", key="cta", on_click=open_passcode)
        if st.session_state.get("show_passcode"):
            passcode_card()
    right.markdown(HERO_PREVIEW, unsafe_allow_html=True)

    # Three quick-start cards. Each one opens the passcode card, then asks Paige that question.
    st.write("")
    with st.container(key="cards"):
        for column, (label, icon, question) in zip(st.columns(3, gap="medium"), HOME_CARDS):
            column.button(
                label,
                key=f"card_{label}",
                icon=icon,
                use_container_width=True,
                on_click=open_passcode,
                args=(question,),
            )

    # A quiet strip of facts (copied from the FAQ sheet; update them here if the sheet changes).
    st.markdown(
        "<div class='info-strip'>"
        "<span><b>Free delivery</b> on orders above ₹499</span>"
        "<span><b>7-day returns</b> on most items</span>"
        "<span><b>Support</b> 9 AM to 9 PM, all days</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def ask_suggested(question):
    """Called when a suggested question is clicked: remember it so it is sent to Paige."""
    st.session_state.clicked_question = question


def chat_page():
    page_width("100%", "0.5rem", "2.5rem")
    # Left bar: big logo, suggested questions, this chat's tickets, and "Start a new chat" at the very bottom.
    sidebar = st.sidebar.container(key="sidebar_body")
    with sidebar:
        st.image(LOGO_FILE, width=260)
        st.subheader("Suggested Questions")
        with st.container(key="suggested"):
            for number, question in enumerate(SUGGESTED_QUESTIONS):
                st.button(
                    question,
                    key=f"suggest_{number}",
                    type="tertiary",
                    use_container_width=True,
                    on_click=ask_suggested,
                    args=(question,),
                )

    # The page title sits at the very top of the page.
    st.title("PaperLeaf Books Support")

    # The conversation: the customer on the right, Paige on the left.
    for index, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.container(key=f"user_{index}"):
                bubble(message["text"])
        else:
            with st.container(key=f"paige_{index}"):
                with st.container():
                    bubble(message["text"])
                    if index > 0:  # every reply (not the opening greeting) can be rated
                        show_feedback(index)

    # The message is what the customer typed, or the question they clicked.
    typed = st.chat_input("Type your message here...")
    prompt = typed or st.session_state.pop("clicked_question", None)
    if prompt:
        session_id = st.session_state.session_id
        st.session_state.messages.append({"role": "user", "text": prompt})
        save_message(session_id, "user", prompt)
        with st.container(key="user_new"):
            bubble(prompt)
        with st.container(key="paige_new"):
            with st.container():
                bubble("<span class='typing'><i></i><i></i><i></i></span>", html=True)  # shown while Paige answers
                try:
                    reply = run_async(ask_paige(session_id, prompt)) or "Sorry, I could not answer that. Please try again."
                except Exception:
                    reply = "Sorry, something went wrong on our side. Please try again in a minute."
        st.session_state.messages.append({"role": "assistant", "text": reply})
        save_message(session_id, "assistant", reply)
        st.rerun()  # redraw the chat so the new reply shows with its feedback buttons

    # The sidebar shows only the tickets Paige created in THIS chat (found by the ticket IDs in her replies).
    # A customer never sees anyone else's tickets.
    my_ticket_ids = set()
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            my_ticket_ids.update(re.findall(r"TKT-\d+", message["text"]))
    with sidebar:
        show_open_tickets(only_ids=my_ticket_ids)
        st.button("Start a new chat", key="newchat", on_click=leave_chat)


def admin_page():
    page_width("100%", "0.5rem", "2.5rem")
    with st.sidebar.container(key="sidebar_body"):
        st.image(LOGO_FILE, width=260)
        show_open_tickets()
        st.button("Log out", key="newchat", on_click=leave_chat)
    st.title("Admin: all chats")

    # Group the saved messages by chat, newest chat first.
    chats = {}
    for row in read_csv(CHATS_FILE):
        chats.setdefault(row["session_id"], []).append(row)
    if not chats:
        st.info("No chats yet.")
    for number, (session_id, rows) in enumerate(reversed(list(chats.items()))):
        first_question = next((r["message"] for r in rows if r["role"] == "user"), "(no questions yet)")
        with st.expander(f"{rows[0]['time']} · {first_question[:60]}"):
            # The same bubbles the customer saw: customer on the right, Paige on the left.
            for position, row in enumerate(rows):
                if row["role"] == "user":
                    with st.container(key=f"user_admin{number}_{position}"):
                        bubble(row["message"])
                else:
                    with st.container(key=f"paige_admin{number}_{position}"):
                        with st.container():
                            bubble(row["message"])


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
    chat_page()
else:
    home_page()
