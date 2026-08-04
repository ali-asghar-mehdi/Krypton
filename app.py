import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import sqlite3
import json
import urllib.parse

st.set_page_config(page_title="AI Workspace", layout="wide")

DB_FILE = "chats.db"

# ---------- DB SETUP ----------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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

init_db()

def load_chats():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT title, messages FROM chats")
        rows = c.fetchall()
    chats = {title: json.loads(msgs) for title, msgs in rows}
    if not chats:
        chats = {"New Chat": []}
    return chats

def load_trash():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT title, messages FROM trash_chats")
        rows = c.fetchall()
    return {title: json.loads(msgs) for title, msgs in rows}

def save_chat(title, messages):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO chats (title, messages) VALUES (?, ?)", (title, json.dumps(messages)))

def save_trash(title, messages):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO trash_chats (title, messages) VALUES (?, ?)", (title, json.dumps(messages)))

def move_to_trash(title, messages):
    save_trash(title, messages)
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chats WHERE title = ?", (title,))

def restore_chat(title):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT messages FROM trash_chats WHERE title = ?", (title,))
        row = c.fetchone()
        if row:
            messages = json.loads(row[0])
            save_chat(title, messages)
            c.execute("DELETE FROM trash_chats WHERE title = ?", (title,))

@st.cache_data
def load_memory_from_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT instructions FROM global_memory WHERE id = 1")
        row = c.fetchone()
    return row[0] if row else ""

def save_memory_to_db(text):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO global_memory (id, instructions) VALUES (1, ?)", (text,))
    st.cache_data.clear()

# ---------- CACHED CLIENT ----------
@st.cache_resource
def get_groq_client():
    return Groq(api_key=st.secrets["GROQ_API_KEY"])

client = get_groq_client()

# ---------- SESSION STATE ----------
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()

if "trash_chats" not in st.session_state:
    st.session_state.trash_chats = load_trash()

if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

if "trash_current_chat" not in st.session_state:
    st.session_state.trash_current_chat = None

if "mode" not in st.session_state:
    st.session_state.mode = "normal"  # "normal" or "trash"

if "global_memory" not in st.session_state:
    st.session_state.global_memory = load_memory_from_db()

if "theme_choice" not in st.session_state:
    st.session_state.theme_choice = "1. Minimal Dark (Gemini Gray)"

if "rename_target" not in st.session_state:
    st.session_state.rename_target = None

if "tip_index" not in st.session_state:
    st.session_state.tip_index = 0

# ---------- TIPS ----------
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

# ---------- THEMES ----------
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

# ---------- UTIL ----------
def get_voice_audio(text):
    tts = gTTS(text=text, lang='en', tld='com')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

def generate_chat_title(first_prompt):
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Generate a short title (2-4 words). No punctuation."},
                {"role": "user", "content": first_prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"Chat {len(st.session_state.chats)}"

def rename_chat(old_title, new_title):
    new_title = new_title.strip()
    if not new_title or new_title in st.session_state.chats:
        return False
    st.session_state.chats[new_title] = st.session_state.chats.pop(old_title)
    save_chat(new_title, st.session_state.chats[new_title])
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chats WHERE title = ?", (old_title,))
    if st.session_state.current_chat == old_title:
        st.session_state.current_chat = new_title
    return True

def generate_ai_stream(prompt, messages_history):
    image_keywords = ["draw", "image", "picture", "photo", "illustration", "paint", "sketch", "render"]
    video_keywords = ["video", "clip", "movie", "animation"]
    p_lower = prompt.lower()

    if any(k in p_lower for k in video_keywords) and any(a in p_lower for a in ["make", "create", "generate", "show", "give"]):
        encoded = urllib.parse.quote(prompt)
        yield f"Here is your video:\nhttps://image.pollinations.ai/prompt/{encoded}?model=video"
    elif any(k in p_lower for k in image_keywords):
        encoded = urllib.parse.quote(prompt)
        yield f"https://image.pollinations.ai/prompt/{encoded}"
    else:
        system_instruction = (
            "You are Krypton. You do not mention training data, training cutoffs, knowledge limits, or dates like '2023'. "
            "You never say you are outdated or limited. You respond confidently using the information in this conversation "
            f"and the user's memory. Follow these rules: {st.session_state.global_memory}"
        )
        api_messages = [{"role": "system", "content": system_instruction}] + messages_history
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

# ---------- SIDEBAR ----------
with st.sidebar:
    tab_chats, tab_memory, tab_themes = st.tabs(["💬 Chats", "🧠 Memory", "🎨 Themes"])

    # CHATS TAB
    with tab_chats:
        if st.button("+ New Chat", type="primary", use_container_width=True):
            new_id = f"New Chat {len(st.session_state.chats) + 1}"
            st.session_state.chats[new_id] = []
            st.session_state.current_chat = new_id
            st.session_state.mode = "normal"
            save_chat(new_id, [])
            st.rerun()

        st.caption("Recent Conversations")
        for name in list(st.session_state.chats.keys()):
            col1, col2 = st.columns([5, 2])
            with col1:
                if st.button(name, key=f"chat_{name}", use_container_width=True):
                    st.session_state.current_chat = name
                    st.session_state.mode = "normal"
                    st.rerun()
            with col2:
                if st.button("✏️", key=f"rename_{name}"):
                    st.session_state.rename_target = name
                if st.button("🗑️", key=f"delete_{name}") and len(st.session_state.chats) > 1:
                    move_to_trash(name, st.session_state.chats[name])
                    del st.session_state.chats[name]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.session_state.trash_chats = load_trash()
                    st.session_state.mode = "normal"
                    st.rerun()

        tip = get_next_tip()
        st.markdown(
            f"""
            <div class="tip-card">
                <strong>💡 Krypton Tip</strong><br>
                {tip}
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.session_state.rename_target:
            st.divider()
            st.subheader(f"Rename: {st.session_state.rename_target}")
            new_name = st.text_input("New name:", key="rename_input")
            col_ok, col_cancel = st.columns(2)
            with col_ok:
                if st.button("Save"):
                    if rename_chat(st.session_state.rename_target, new_name):
                        st.session_state.rename_target = None
                        st.rerun()
                    else:
                        st.warning("Invalid or duplicate name.")
            with col_cancel:
                if st.button("Cancel"):
                    st.session_state.rename_target = None
                    st.rerun()

    # MEMORY + TRASH TAB
    with tab_memory:
        st.caption("Global instructions for Krypton:")
        mem_input = st.text_area("Persona & Rules:", value=st.session_state.global_memory, height=120)
        if st.button("Save Memory", use_container_width=True):
            st.session_state.global_memory = mem_input
            save_memory_to_db(mem_input)
            st.success("Saved!")

        st.divider()
        st.subheader("🗑️ Trash — Deleted Chats")

        st.session_state.trash_chats = load_trash()
        trash = st.session_state.trash_chats

        if not trash:
            st.caption("No deleted chats yet.")
        else:
            for title in list(trash.keys()):
                st.write(f"**{title}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"Open {title}", key=f"open_trash_{title}"):
                        st.session_state.mode = "trash"
                        st.session_state.trash_current_chat = title
                        st.rerun()
                with col2:
                    if st.button(f"Restore {title}", key=f"restore_{title}"):
                        restore_chat(title)
                        st.session_state.chats = load_chats()
                        st.session_state.trash_chats = load_trash()
                        st.session_state.mode = "normal"
                        st.session_state.current_chat = title
                        st.session_state.trash_current_chat = None
                        st.rerun()
                with col3:
                    if st.button(f"Delete Permanently {title}", key=f"purge_{title}"):
                        with sqlite3.connect(DB_FILE) as conn:
                            c = conn.cursor()
                            c.execute("DELETE FROM trash_chats WHERE title = ?", (title,))
                        st.session_state.trash_chats = load_trash()
                        if st.session_state.mode == "trash" and st.session_state.trash_current_chat == title:
                            st.session_state.mode = "normal"
                            st.session_state.trash_current_chat = None
                        st.rerun()

    # THEMES TAB
    with tab_themes:
        st.caption("Choose your design preset:")
        options = list(themes_db.keys())
        selected = st.selectbox(
            "Theme Presets:",
            options,
            index=options.index(st.session_state.theme_choice)
        )
        st.session_state.theme_choice = selected

# ---------- HEADER ----------
col_h1, col_h2 = st.columns([4, 2])
with col_h1:
    if st.session_state.mode == "normal":
        st.markdown("### 💬 Chat")
    else:
        st.markdown(f"### 🗑️ Trash Chat — {st.session_state.trash_current_chat}")
with col_h2:
    if st.button("Clear Screen", use_container_width=True):
        if st.session_state.mode == "normal":
            st.session_state.chats[st.session_state.current_chat] = []
            save_chat(st.session_state.current_chat, [])
        else:
            st.session_state.trash_chats[st.session_state.trash_current_chat] = []
            save_trash(st.session_state.trash_current_chat, [])
        st.rerun()
    if st.session_state.mode == "trash":
        if st.button("⬅ Back to Chats", use_container_width=True):
            st.session_state.mode = "normal"
            st.session_state.trash_current_chat = None
            st.rerun()

# ---------- MAIN CHAT DISPLAY ----------
if st.session_state.mode == "normal":
    active_messages = st.session_state.chats[st.session_state.current_chat]
else:
    active_messages = st.session_state.trash_chats.get(st.session_state.trash_current_chat, [])

for idx, msg in enumerate(active_messages):
    with st.chat_message(msg["role"]):
        content = msg["content"]
        st.write(content)

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔊", key=f"voice_{st.session_state.mode}_{idx}"):
                audio = get_voice_audio(content)
                st.audio(audio, format="audio/mp3", autoplay=True)
        with col2:
            with st.expander("More", expanded=False):
                if msg["role"] == "user":
                    new_text = st.text_input("Edit message:", value=content, key=f"edit_{st.session_state.mode}_{idx}")
                    if st.button("Save & Resend", key=f"save_edit_{st.session_state.mode}_{idx}"):
                        edited = active_messages[:idx]
                        edited.append({"role": "user", "content": new_text})
                        if st.session_state.mode == "normal":
                            st.session_state.chats[st.session_state.current_chat] = edited
                            save_chat(st.session_state.current_chat, edited)
                        else:
                            st.session_state.trash_chats[st.session_state.trash_current_chat] = edited
                            save_trash(st.session_state.trash_current_chat, edited)
                        st.rerun()
                if st.button("⏪ Rewind to here", key=f"rewind_{st.session_state.mode}_{idx}"):
                    rewound = active_messages[:idx + 1]
                    if st.session_state.mode == "normal":
                        st.session_state.chats[st.session_state.current_chat] = rewound
                        save_chat(st.session_state.current_chat, rewound)
                    else:
                        st.session_state.trash_chats[st.session_state.trash_current_chat] = rewound
                        save_trash(st.session_state.trash_current_chat, rewound)
                    st.rerun()
                if st.button("Delete message", key=f"del_msg_{st.session_state.mode}_{idx}"):
                    active_messages.pop(idx)
                    if st.session_state.mode == "normal":
                        st.session_state.chats[st.session_state.current_chat] = active_messages
                        save_chat(st.session_state.current_chat, active_messages)
                    else:
                        st.session_state.trash_chats[st.session_state.trash_current_chat] = active_messages
                        save_trash(st.session_state.trash_current_chat, active_messages)
                    st.rerun()

# REGENERATE BUTTON
if active_messages and active_messages[-1]["role"] == "assistant":
    if st.button("🔄 Regenerate Response"):
        active_messages.pop()
        last_user_prompt = active_messages[-1]["content"] if active_messages else ""
        if last_user_prompt:
            with st.chat_message("assistant"):
                stream = generate_ai_stream(last_user_prompt, active_messages)
                full_response = st.write_stream(stream)
            active_messages.append({"role": "assistant", "content": full_response})
            if st.session_state.mode == "normal":
                st.session_state.chats[st.session_state.current_chat] = active_messages
                save_chat(st.session_state.current_chat, active_messages)
            else:
                st.session_state.trash_chats[st.session_state.trash_current_chat] = active_messages
                save_trash(st.session_state.trash_current_chat, active_messages)
            st.rerun()

# ---------- INPUT ----------
if st.session_state.mode == "normal":
    user_prompt = st.chat_input("Ask anything...")
else:
    user_prompt = st.chat_input("Continue deleted chat...")

if user_prompt:
    if st.session_state.mode == "normal" and len(active_messages) == 0:
        auto_title = generate_chat_title(user_prompt)
        old = st.session_state.current_chat
        rename_chat(old, auto_title)
        active_messages = st.session_state.chats[st.session_state.current_chat]

    active_messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.write(user_prompt)

    with st.chat_message("assistant"):
        stream = generate_ai_stream(user_prompt, active_messages)
        full_response = st.write_stream(stream)

    active_messages.append({"role": "assistant", "content": full_response})

    if st.session_state.mode == "normal":
        st.session_state.chats[st.session_state.current_chat] = active_messages
        save_chat(st.session_state.current_chat, active_messages)
    else:
        st.session_state.trash_chats[st.session_state.trash_current_chat] = active_messages
        save_trash(st.session_state.trash_current_chat, active_messages)

    st.rerun()
