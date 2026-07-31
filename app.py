import streamlit as st
from groq import Groq
from gtts import gTTS
import io
import sqlite3
import json
import urllib.parse
from PIL import Image

st.set_page_config(page_title="My AI Chatbot", layout="wide")

# --- DATABASE SETUP (SQLite) ---
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

# Initialize Database
init_db()

# Connect to Groq API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "chats" not in st.session_state:
    st.session_state.chats = load_chats_from_db()

if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

if "global_memory" not in st.session_state:
    st.session_state.global_memory = load_memory_from_db()

if "theme_choice" not in st.session_state:
    st.session_state.theme_choice = "1. Classic (Blue & Purple)"

def generate_chat_title(first_prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Generate a short title (2-4 words max) for a chat starting with this prompt. No quotes or punctuation."},
                {"role": "user", "content": first_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Chat {len(st.session_state.chats)}"

def get_voice_audio(text):
    tts = gTTS(text=text, lang='en', tld='com')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# --- SIDEBAR WITH TABS ---
with st.sidebar:
    st.header("Control Center")
    tab_chats, tab_memory, tab_themes, tab_settings = st.tabs(["💬 Chats", "🧠 Memory", "🎨 Themes", "⚙️ Settings"])
    
    with tab_chats:
        st.subheader("Chat Sessions")
        if st.button("+ New Chat", type="primary", use_container_width=True):
            new_id = f"New Chat {len(st.session_state.chats) + 1}"
            st.session_state.chats[new_id] = []
            st.session_state.current_chat = new_id
            save_chat_to_db(new_id, [])
            st.rerun()

        st.divider()
        
        chat_names = list(st.session_state.chats.keys())
        for chat_name in chat_names:
            col_select, col_edit, col_del = st.columns([3, 1, 1])
            
            with col_select:
                if st.button(chat_name, key=f"select_{chat_name}", use_container_width=True):
                    st.session_state.current_chat = chat_name
                    st.rerun()
                    
            with col_edit:
                with st.popover("✏️"):
                    new_name = st.text_input("Rename Chat:", value=chat_name, key=f"rename_{chat_name}")
                    if st.button("Save", key=f"save_{chat_name}"):
                        if new_name and new_name != chat_name:
                            st.session_state.chats[new_name] = st.session_state.chats.pop(chat_name)
                            rename_chat_in_db(chat_name, new_name)
                            if st.session_state.current_chat == chat_name:
                                st.session_state.current_chat = new_name
                            st.rerun()

        with col_del:
            if len(st.session_state.chats) > 1:
                if st.button("🗑️", key=f"del_{chat_name}"):
                    del st.session_state.chats[chat_name]
                    delete_chat_from_db(chat_name)
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

        st.divider()
        st.subheader("⏪ Rewind Chat")
        
        active_messages = st.session_state.chats[st.session_state.current_chat]
        for idx, msg in enumerate(active_messages):
            role_label = "You" if msg["role"] == "user" else "AI"
            preview = msg["content"][:18] + "..." if len(msg["content"]) > 18 else msg["content"]
            if st.button(f"[{role_label}] {preview}", key=f"side_rewind_{idx}", use_container_width=True):
                st.session_state.chats[st.session_state.current_chat] = active_messages[:idx + 1]
                save_chat_to_db(st.session_state.current_chat, st.session_state.chats[st.session_state.current_chat])
                st.rerun()

    with tab_memory:
        st.subheader("🧠 Global Memory")
        st.caption("Instructions saved here apply to ALL chats:")
        user_memory_input = st.text_area("Persona & Rules:", value=st.session_state.global_memory, height=120)
        if st.button("Save Memory", use_container_width=True):
            st.session_state.global_memory = user_memory_input
            save_memory_to_db(user_memory_input)
            st.success("Global memory updated!")

    with tab_themes:
        st.subheader("🎨 Theme Presets")
        theme_options = [
            "1. Classic (Blue & Purple)",
            "2. Cyberpunk (Neon Cyan & Pink)",
            "3. Ocean Soft (Slate & Mint)",
            "4. Sunset Vibes (Orange & Deep Rose)",
            "5. Forest Night (Emerald & Lime)",
            "6. Royal Gold (Gold & Deep Violet)",
            "7. Crimson Dark (Red & Charcoal)",
            "8. Lavender Dream (Lilac & Indigo)",
            "9. Midnight OLED (True Black & Silver)",
            "10. Matrix Green (Matrix Green & Dark Moss)"
        ]
        
        selected_theme = st.selectbox(
            "Choose Theme Preset:",
            theme_options,
            index=theme_options.index(st.session_state.theme_choice) if st.session_state.theme_choice in theme_options else 0
        )
        st.session_state.theme_choice = selected_theme

    with tab_settings:
        st.subheader("Preferences")
        dark_mode = st.toggle("🌙 Dark Mode", value=True)

# --- 10 THEME DEFINITIONS ---
themes_db = {
    "1. Classic (Blue & Purple)": {
        "app_bg": "#0E0F12", "sidebar_bg": "#1C1C1E", "user": "#007AFF", "ai": "#AF52DE"
    },
    "2. Cyberpunk (Neon Cyan & Pink)": {
        "app_bg": "#050B14", "sidebar_bg": "#0A1428", "user": "#00F0FF", "ai": "#FF007F"
    },
    "3. Ocean Soft (Slate & Mint)": {
        "app_bg": "#0F172A", "sidebar_bg": "#1E293B", "user": "#38BDF8", "ai": "#34D399"
    },
    "4. Sunset Vibes (Orange & Deep Rose)": {
        "app_bg": "#180B10", "sidebar_bg": "#2D121C", "user": "#FF7A00", "ai": "#E91E63"
    },
    "5. Forest Night (Emerald & Lime)": {
        "app_bg": "#06140C", "sidebar_bg": "#0D2617", "user": "#10B981", "ai": "#84CC16"
    },
    "6. Royal Gold (Gold & Deep Violet)": {
        "app_bg": "#120B18", "sidebar_bg": "#21142B", "user": "#F59E0B", "ai": "#8B5CF6"
    },
    "7. Crimson Dark (Red & Charcoal)": {
        "app_bg": "#140505", "sidebar_bg": "#260A0A", "user": "#EF4444", "ai": "#64748B"
    },
    "8. Lavender Dream (Lilac & Indigo)": {
        "app_bg": "#110E1B", "sidebar_bg": "#1F1A30", "user": "#A855F7", "ai": "#6366F1"
    },
    "9. Midnight OLED (True Black & Silver)": {
        "app_bg": "#000000", "sidebar_bg": "#121212", "user": "#3B82F6", "ai": "#94A3B8"
    },
    "10. Matrix Green (Matrix Green & Dark Moss)": {
        "app_bg": "#020D04", "sidebar_bg": "#061F09", "user": "#22C55E", "ai": "#14B8A6"
    }
}

active_theme = themes_db.get(st.session_state.theme_choice, themes_db["1. Classic (Blue & Purple)"])

# Dynamic Styling Override
if dark_mode:
    st.markdown(
        f"""
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
            background-color: {active_theme['app_bg']} !important;
            color: #F2F2F7 !important;
        }}
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
            background-color: {active_theme['sidebar_bg']} !important;
        }}

        /* User Message & Avatar */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
            background-color: {active_theme['user']}22 !important;
            border-left: 4px solid {active_theme['user']} !important;
            border-radius: 12px !important;
        }}
        [data-testid="stChatMessageAvatarUser"] {{
            background-color: {active_theme['user']} !important;
            color: #ffffff !important;
        }}

        /* AI Message & Avatar */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
            background-color: {active_theme['ai']}22 !important;
            border-left: 4px solid {active_theme['ai']} !important;
            border-radius: 12px !important;
        }}
        [data-testid="stChatMessageAvatarAssistant"] {{
            background-color: {active_theme['ai']} !important;
            color: #ffffff !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- DASHBOARD HEADER ---
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.title("⚡ My AI Chatbot")
    st.caption("Powered by Groq & Pollinations AI")

with header_col2:
    if st.button("🗑️ Clear Screen", use_container_width=True):
        st.session_state.chats[st.session_state.current_chat] = []
        save_chat_to_db(st.session_state.current_chat, [])
        st.rerun()

st.divider()

# --- MESSAGES DISPLAY ---
active_messages = st.session_state.chats[st.session_state.current_chat]

for idx, message in enumerate(active_messages):
    with st.chat_message(message["role"]):
        with st.container(border=True):
            st.write(message["content"])
            
            if "IMAGE_URL:" in message["content"]:
                img_url = message["content"].split("IMAGE_URL:")[1].strip()
                st.image(img_url, caption="Generated Image")
            elif "VIDEO_URL:" in message["content"]:
                vid_url = message["content"].split("VIDEO_URL:")[1].strip()
                st.video(vid_url)

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🔊 Voice", key=f"voice_{idx}"):
                    clean_text = message["content"].split("IMAGE_URL:")[0].split("VIDEO_URL:")[0]
                    audio_data = get_voice_audio(clean_text)
                    st.audio(audio_data, format="audio/mp3", autoplay=True)
            with col2:
                with st.expander("⚙️ Options"):
                    if message["role"] == "user":
                        new_text = st.text_input("Edit message:", value=message["content"], key=f"edit_input_{idx}")
                        if st.button("Save & Resend", key=f"save_edit_{idx}"):
                            st.session_state.chats[st.session_state.current_chat] = active_messages[:idx]
                            st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": new_text})
                            save_chat_to_db(st.session_state.current_chat, st.session_state.chats[st.session_state.current_chat])
                            st.rerun()
                    
                    if st.button("⏪ Rewind to here", key=f"rewind_msg_{idx}"):
                        st.session_state.chats[st.session_state.current_chat] = active_messages[:idx + 1]
                        save_chat_to_db(st.session_state.current_chat, st.session_state.chats[st.session_state.current_chat])
                        st.rerun()

                    if st.button("🗑️ Delete this message", key=f"del_msg_{idx}"):
                        active_messages.pop(idx)
                        save_chat_to_db(st.session_state.current_chat, active_messages)
                        st.rerun()

# --- ATTACHMENT POPOVER ---
with st.popover("📎 Attach File / Image"):
    uploaded_file = st.file_uploader("Upload file:", type=["png", "jpg", "jpeg", "txt"])
    file_context = ""
    if uploaded_file is not None:
        if uploaded_file.type.startswith("image/"):
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_container_width=True)
            file_context = f"\n[User attached an image named {uploaded_file.name}]"
        elif uploaded_file.type == "text/plain":
            file_text = uploaded_file.read().decode("utf-8")
            file_context = f"\n[Attached file content:\n{file_text}]"

# --- CHAT INPUT ---
user_prompt = st.chat_input("Type your message here...")

# --- HANDLE SUBMIT ---
if user_prompt:
    full_prompt = user_prompt + file_context
    
    if len(active_messages) == 0:
        auto_title = generate_chat_title(user_prompt)
        current_id = st.session_state.current_chat
        
        st.session_state.chats[auto_title] = st.session_state.chats.pop(current_id)
        delete_chat_from_db(current_id)
        st.session_state.current_chat = auto_title
        active_messages = st.session_state.chats[auto_title]

    active_messages.append({"role": "user", "content": full_prompt})
    
    image_keywords = ["draw", "image", "picture", "photo", "illustration", "paint", "sketch", "render"]
    video_keywords = ["video", "clip", "movie", "animation"]
    
    p_lower = user_prompt.lower()
    
    if any(k in p_lower for k in video_keywords) and any(action in p_lower for action in ["make", "create", "generate", "show", "give"]):
        encoded_prompt = urllib.parse.quote(user_prompt)
        video_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=video"
        bot_reply = f"Here is your video!\nVIDEO_URL:{video_url}"
    elif any(k in p_lower for k in image_keywords):
        encoded_prompt = urllib.parse.quote(user_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        bot_reply = f"Here is your image!\nIMAGE_URL:{image_url}"
    else:
        system_memory_instruction = f"You are a friendly, helpful AI assistant. Always follow these persistent user rules and memory instructions: {st.session_state.global_memory}"
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
