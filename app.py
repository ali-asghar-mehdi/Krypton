import streamlit as st
from groq import Groq
import sqlite3
import json
import urllib.parse
from gtts import gTTS
import io

st.set_page_config(page_title="AI Workspace", layout="wide")

DB_FILE = "chats.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            title TEXT PRIMARY KEY,
            messages TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trash_chats (
            title TEXT PRIMARY KEY,
            messages TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS global_memory (
            id INTEGER PRIMARY KEY,
            instructions TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

def load_chats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, messages FROM chats")
    rows = c.fetchall()
    conn.close()
    return {title: json.loads(msgs) for title, msgs in rows}

def load_trash():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, messages FROM trash_chats")
    rows = c.fetchall()
    conn.close()
    return {title: json.loads(msgs) for title, msgs in rows}

def save_chat(title, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO chats (title, messages) VALUES (?, ?)", (title, json.dumps(messages)))
    conn.commit()
    conn.close()

def save_trash(title, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO trash_chats (title, messages) VALUES (?, ?)", (title, json.dumps(messages)))
    conn.commit()
    conn.close()

def move_to_trash(title, messages):
    save_trash(title, messages)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE title = ?", (title,))
    conn.commit()

    # --- SESSION STATE ---
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()

if "trash_chats" not in st.session_state:
    st.session_state.trash_chats = load_trash()

if "current_chat" not in st.session_state:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

if "trash_current_chat" not in st.session_state:
    st.session_state.trash_current_chat = None

if "global_memory" not in st.session_state:
    st.session_state.global_memory = load_memory_from_db()

if "theme_choice" not in st.session_state:
    st.session_state.theme_choice = "1. Minimal Dark (Gemini Gray)"

if "rename_target" not in st.session_state:
    st.session_state.rename_target = None

if "tip_index" not in st.session_state:
    st.session_state.tip_index = 0

# --- TIPS ---
TIPS = [
    "You can rename chats from the sidebar.",
    "Krypton can generate images — just ask.",
    "Use Memory to customize Krypton’s personality.",
    "You can rewind any chat from the sidebar.",
    "Try switching to OLED Pitch Black theme.",
    "Krypton remembers your preferences during the session."
]

def get_next_tip():
    st.session_state.tip_index = (st.session_state.tip_index + 1) % len(TIPS)
    return TIPS[st.session_state.tip_index]

# --- THEMES ---
themes_db = {
    "1. Minimal Dark (Gemini Gray)": {"app_bg": "#131314", "sidebar_bg": "#1E1F20", "user": "#2F2F32", "ai": "#1A73E8"},
    "2. ChatGPT Dark (Classic Charcoal)": {"app_bg": "#212121", "sidebar_bg": "#171717", "user": "#2F2F2F", "ai": "#10A37F"},
    "3. Cyberpunk (Neon Blue & Pink)": {"app_bg": "#050B14", "sidebar_bg": "#0A1428", "user": "#00F0FF", "ai": "#FF007F"},
    "4. Ocean Slate (Deep Aqua)": {"app_bg": "#0F172A", "sidebar_bg": "#1E293B", "user": "#38BDF8", "ai": "#34D399"},
    "5. Sunset Glow (Orange Accent)": {"app_bg": "#180B10", "sidebar_bg": "#2D121C", "user": "#FF7A00", "ai": "#E91E63"},
    "6. Forest Night (Emerald)": {"app_bg": "#06140C", "sidebar_bg": "#0D2617", "user": "#10B981", "ai": "#84CC16"},
    "7. Royal Violet (Purple Minimal)": {"app_bg": "#120B18", "sidebar_bg": "#21142B", "user": "#F59E0B", "ai": "#8B5CF6"},
    "8. Crimson Dark (Charcoal & Red)": {"app_bg": "#140505", "sidebar_bg": "#260A0A", "user": "#EF4444", "ai": "#64748B"},
    "9. Lavender Glow (Soft Lilac)": {"app_bg": "#110E1B", "sidebar_bg": "#1F1A30", "user": "#A855F7", "ai": "#6366F1"},
    "10. OLED Pitch Black": {"app_bg": "#000000", "sidebar_bg": "#121212", "user": "#262626", "ai": "#3B82F6"}
}

active_theme = themes_db[st.session_state.theme_choice]

# --- CSS ---
st.markdown(
    f"""
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: {active_theme['app_bg']} !important;
        color: #E3E3E3 !important;
    }}
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
        background-color: {active_theme['sidebar_bg']} !important;
    }}
    [data-testid="stChatMessage"] {{
        background-color: transparent !important;
        border: none !important;
        padding: 8px 0px !important;
    }}
    [data-testid="stChatMessageAvatarUser"] {{
        background-color: {active_theme['user']} !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stChatMessageAvatarAssistant"] {{
        background-color: {active_theme['ai']} !important;
        color: #FFFFFF !important;
    }}
    .stButton > button {{
        border-radius: 8px !important;
        border: 1px solid #333336 !important;
        background-color: transparent !important;
        color: #E3E3E3 !important;
    }}
    .stButton > button:hover {{
        border-color: #55555A !important;
        background-color: #2F2F32 !important;
    }}
    .tip-card {{
        padding: 12px;
        border-radius: 8px;
        background-color: #1E1F20;
        border: 1px solid #2A2B2D;
        margin-top: 10px;
        font-size: 14px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

    conn.close()
