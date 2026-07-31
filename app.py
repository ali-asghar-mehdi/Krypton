import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import sqlite3
import json
import urllib.parse
from PIL import Image

st.set_page_config(page_title="AI Workspace", layout="wide")

# --- DATABASE SETUP ---
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
        CREATE TABLE IF NOT EXISTS global_memory (
            id INTEGER PRIMARY KEY,
            instructions TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_chats_from_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, messages FROM chats")
    rows = c.fetchall()
    conn.close()

    chats = {}
    for title, msgs_json in rows:
        chats[title] = json.loads(msgs_json)

    if not chats:
        chats = {"New Chat": []}
    return chats

def save_chat_to_db(title, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO chats (title, messages) VALUES (?, ?)",
        (title, json.dumps(messages))
    )
    conn.commit()
    conn.close()

def delete_chat_from_db(title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE title = ?", (title,))
    conn.commit()
    conn.close()

def rename_chat_in_db(old_title, new_title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT messages FROM chats WHERE title = ?", (old_title,))
    row = c.fetchone()
    if row:
        msgs = row[0]
        c.execute("DELETE FROM chats WHERE title = ?", (old_title,))
        c.execute("INSERT OR REPLACE INTO chats (title, messages) VALUES (?, ?)", (new_title, msgs))
    conn.commit()
    conn.close()

def load_memory_from_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT instructions FROM global_memory WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def save_memory_to_db(memory_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO global_memory (id, instructions) VALUES (1, ?)", (memory_text,))
    conn.commit()
    conn.close()

init_db()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- SESSION STATE ---
if "chats" not in st.session_state:
    st.session_state.chats = load_chats_from_db()

if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

if "global_memory" not in st.session_state:
    st.session_state.global_memory = load_memory_from_db()

if "theme_choice" not in st.session_state:
    st.session_state.theme_choice = "1. Minimal Dark (Gemini Gray)"

if "rename_target" not in st.session_state:
    st.session_state.rename_target = None

# --- RENAME CHAT ---
def rename_chat(old_title, new_title):
    new_title = new_title.strip()
    if not new_title:
        return False
    if new_title in st.session_state.chats:
        return False

    st.session_state.chats[new_title] = st.session_state.chats.pop(old_title)
    rename_chat_in_db(old_title, new_title)

    if st.session_state.current_chat == old_title:
        st.session_state.current_chat = new_title

    return True

# --- TITLE GENERATION ---
def generate_chat_title(first_prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Generate a short title (2-4 words max). No punctuation."},
                {"role": "user", "content": first_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Chat {len(st.session_state.chats)}"

# --- TTS ---
def get_voice_audio(text):
    tts = gTTS(text=text, lang='en', tld='com')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

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

# --- ORIGINAL CSS ---
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
    </style>
    """,
    unsafe_allow_html=True
)

# --- SIDEBAR ---
with st.sidebar:
    tab_chats, tab_memory, tab_themes = st.tabs(["💬 Chats", "🧠 Memory", "🎨 Themes"])

    # --- CHATS TAB ---
    with tab_chats:
        if st.button("+ New Chat", type="primary", use_container_width=True):
            new_id = f"New Chat {len(st.session_state.chats) + 1}"
            st.session_state.chats[new_id] = []
            st.session_state.current_chat = new_id
            save_chat_to_db(new_id, [])
            st.rerun()

        st.caption("Recent Conversations")

        chat_names = list(st.session_state.chats.keys())

        for chat_name in chat_names:
            col1, col2 = st.columns([5, 2])

            with col1:
                if st.button(chat_name, key=f"select_{chat_name}", use_container_width=True):
                    st.session_state.current_chat = chat_name
                    st.rerun()

            with col2:
                rename_btn = st.button("✏️", key=f"rename_{chat_name}")
                delete_btn = st.button("🗑️", key=f"delete_{chat_name}")

                if rename_btn:
                    st.session_state.rename_target = chat_name

                if delete_btn and len(st.session_state.chats) > 1:
                    del st.session_state.chats[chat_name]
                    delete_chat_from_db(chat_name)
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

        # --- RENAME POPUP ---
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

    # --- MEMORY TAB ---
    with tab_memory:
        st.caption("Instructions saved here apply to ALL chats:")
        user_memory_input = st.text_area("Persona & Rules:", value=st.session_state.global_memory, height=120)
        if st.button("Save Memory", use_container_width=True):
            st.session_state.global_memory = user_memory_input
            save_memory_to_db(user_memory_input)
            st.success("Saved!")

    # --- THEMES TAB ---
    with tab_themes:
        st.caption("Choose your design preset:")
        theme_options = list(themes_db.keys())
        selected_theme = st.selectbox(
            "Theme Presets:",
            theme_options,
            index=theme_options.index(st.session_state.theme_choice)
        )
        st.session_state.theme_choice = selected_theme

# --- HEADER ---
header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.markdown("### 💬 Chat")

with header_col2:
    if st.button("Clear Screen", use_container_width=True):
        st.session_state.chats[st.session_state.current_chat] = []
        save_chat_to_db(st.session_state.current_chat, [])
        st.rerun()

# --- MESSAGE DISPLAY ---
active_messages = st.session_state.chats[st.session_state.current_chat]

for idx, message in enumerate(active_messages):
    with st.chat_message(message["role"]):
        content = message["content"]

        if "IMAGE_URL:" in content:
            text_part, img_url = content.split("IMAGE_URL:")
            if text_part.strip():
                st.write(text_part.strip())
            st.image(img_url.strip(), use_container_width=True)

        elif "VIDEO_URL:" in content:
            text_part, vid_url = content.split("VIDEO_URL:")
            if text_part.strip():
                st.write(text_part.strip())
            st.video(vid_url.strip())

        else:
            st.write(content)

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔊", key=f"voice_{idx}"):
                clean_text = content.split("IMAGE_URL:")[0].split("VIDEO_URL:")[0]
                audio_data = get_voice_audio(clean_text)
                st.audio(audio_data, format="audio/mp3", autoplay=True)

        with col2:
            with st.expander("More", expanded=False):
                if message["role"] == "user":
                    new_text = st.text_input("Edit message:", value=content, key=f"edit_input_{idx}")
                    if st.button("Save & Resend", key=f"save_edit_{idx}"):
                        st.session_state.chats[st.session_state.current_chat] = active_messages[:idx]
                        st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": new_text})
                        save_chat_to_db(st.session_state.current_chat, st.session_state.chats[st.session_state.current_chat])
                        st.rerun()

                if st.button("⏪ Rewind to here", key=f"rewind_msg_{idx}"):
                    st.session_state.chats[st.session_state.current_chat] = active_messages[:idx + 1]
                    save_chat_to_db(st.session_state.current_chat, st.session_state.chats[st.session_state.current_chat])
                    st.rerun()

                if st.button("Delete message", key=f"del_msg_{idx}"):
                    active_messages.pop(idx)
                    save_chat_to_db(st.session_state.current_chat, active_messages)
                    st.rerun()

# --- INPUT AREA ---
user_prompt = st.chat_input("Ask anything...")

if user_prompt:
    if len(active_messages) == 0:
        auto_title = generate_chat_title(user_prompt)
        old_title = st.session_state.current_chat
        rename_chat(old_title, auto_title)
        active_messages = st.session_state.chats[st.session_state.current_chat]

    active_messages.append({"role": "user", "content": user_prompt})

    image_keywords = ["draw", "image", "picture", "photo", "illustration", "paint", "sketch", "render"]
    video_keywords = ["video", "clip", "movie", "animation"]

    p_lower = user_prompt.lower()

    if any(k in p_lower for k in video_keywords) and any(a in p_lower for a in ["make", "create", "generate", "show", "give"]):
        encoded_prompt = urllib.parse.quote(user_prompt)
        video_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=video"
        bot_reply = f"Here is your video:\nIMAGE_URL:{video_url}"

    elif any(k in p_lower for k in image_keywords):
        encoded_prompt = urllib.parse.quote(user_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        bot_reply = f"IMAGE_URL:{image_url}"

    else:
        system_memory_instruction = (
            "You are Krypton, a helpful AI assistant. "
            f"Follow these rules: {st.session_state.global_memory}"
        )

        api_messages = [{"role": "system", "content": system_memory_instruction}] + [
            {"role": m["role"], "content": m["content"]} for m in active_messages
        ]

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages
        )
        bot_reply = response.choices[0].message.content

    active_messages.append({"role": "assistant", "content": bot_reply})
    save_chat_to_db(st.session_state.current_chat, active_messages)
    st.rerun()
