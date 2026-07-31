import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from gtts import gTTS
import io
import sqlite3
import json
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

# Initialize Database on app load
init_db()

# Connect to Groq API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
system_instruction = {"role": "system", "content": "You are a friendly, helpful AI assistant."}

# Load saved chats from database
if "chats" not in st.session_state:
    st.session_state.chats = load_chats_from_db()

if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# Helper function to generate a chat title automatically
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

# Helper function for audio with an American accent
def get_voice_audio(text):
    tts = gTTS(text=text, lang='en', tld='com')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# --- SIDEBAR: Theme, Chat Sessions, & Rewind ---
with st.sidebar:
    st.header("Settings & Theme")
    dark_mode = st.toggle("🌙 Dark Mode", value=False)
    
    st.divider()
    st.header("Chat Sessions")
    
    if st.button("+ New Chat", type="primary"):
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
            if st.button(chat_name, key=f"select_{chat_name}"):
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
    st.header("⏪ Rewind Chat")
    
    active_messages = st.session_state.chats[st.session_state.current_chat]
    for idx, msg in enumerate(active_messages):
        role_label = "You" if msg["role"] == "user" else "AI"
        preview = msg["content"][:18] + "..." if len(msg["content"]) > 18 else msg["content"]
        if st.button(f"[{role_label}] {preview}", key=f"side_rewind_{idx}"):
            st.session_state.chats[st.session_state.current_chat] = active_messages[:idx + 1]
            save_chat_to_db(st.session_state.current_chat, st.session_state.chats[st.session_state.current_chat])
            st.rerun()

# --- CUSTOM STYLING ---
if dark_mode:
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #000000 !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background-color: #111111 !important;
        }
        h1, h2, h3, p, span, label {
            color: #ffffff !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background-color: #002b49 !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background-color: #4b0082 !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

st.title("My AI Chatbot")

# --- DISPLAY MESSAGES ---
active_messages = st.session_state.chats[st.session_state.current_chat]

for idx, message in enumerate(active_messages):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔊 Voice", key=f"voice_{idx}"):
                audio_data = get_voice_audio(message["content"])
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

# --- BOTTOM INPUT AREA ---
st.divider()

file_context = ""

with st.form(key="chat_form", clear_on_submit=True):
    col_attach, col_input, col_send = st.columns([1, 6, 1])
    
    with col_attach:
        with st.popover("📎 Attach"):
            uploaded_file = st.file_uploader("Upload file:", type=["png", "jpg", "jpeg", "txt"])
            if uploaded_file is not None:
                if uploaded_file.type.startswith("image/"):
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded Image", use_container_width=True)
                    file_context = f"\n[User attached an image named {uploaded_file.name}]"
                elif uploaded_file.type == "text/plain":
                    file_text = uploaded_file.read().decode("utf-8")
                    file_context = f"\n[Attached file content:\n{file_text}]"

    with col_input:
        user_prompt = st.text_input("Type your message here...", label_visibility="collapsed")

    with col_send:
        submitted = st.form_submit_button("Send ⬆️", type="primary")

# Auto-focus script to jump to the input box automatically
components.html(
    """
    <script>
        const input = window.parent.document.querySelector('input[type="text"]');
        if (input) {
            input.focus();
        }
    </script>
    """,
    height=0,
)

# --- HANDLE SUBMIT ---
if submitted and user_prompt:
    full_prompt = user_prompt + file_context
    
    if len(active_messages) == 0:
        auto_title = generate_chat_title(user_prompt)
        current_id = st.session_state.current_chat
        
        st.session_state.chats[auto_title] = st.session_state.chats.pop(current_id)
        delete_chat_from_db(current_id)
        st.session_state.current_chat = auto_title
        active_messages = st.session_state.chats[auto_title]

    active_messages.append({"role": "user", "content": full_prompt})
    
    api_messages = [system_instruction] + [
        {"role": m["role"], "content": m["content"]} for m in active_messages
    ]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=api_messages
    )
    
    bot_reply = response.choices[0].message.content
    active_messages.append({"role": "assistant", "content": bot_reply})
    
    # Save updated chat to database
    save_chat_to_db(st.session_state.current_chat, active_messages)
    st.rerun()
