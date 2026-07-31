import streamlit as st
from groq import Groq
from gtts import gTTS
import io
from PIL import Image

st.set_page_config(page_title="My AI Chatbot", layout="wide")

# 1. Initialize chat storage
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# Helper function for audio
def get_voice_audio(text):
    tts = gTTS(text=text, lang='en', tld='com')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# --- SIDEBAR: Theme Toggle & Chat Sessions ---
with st.sidebar:
    st.header("Settings & Theme")
    dark_mode = st.toggle("🌙 Dark Mode", value=False)
    
    st.divider()
    st.header("Chat Sessions")
    
    if st.button("+ New Chat", type="primary"):
        new_id = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[new_id] = []
        st.session_state.current_chat = new_id
        st.rerun()

    st.divider()
    
    # List all chat sessions
    chat_names = list(st.session_state.chats.keys())
    for chat_name in chat_names:
        col_select, col_del = st.columns([3, 1])
        with col_select:
            if st.button(chat_name, key=f"select_{chat_name}"):
                st.session_state.current_chat = chat_name
                st.rerun()
        with col_del:
            if len(st.session_state.chats) > 1:
                if st.button("🗑️", key=f"del_{chat_name}"):
                    del st.session_state.chats[chat_name]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

# --- CUSTOM DARK MODE STYLING ---
if dark_mode:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #000000 !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
        }
        [data-testid="stChatMessage"][aria-label="Chat message from user"] {
            background-color: #002b49 !important;
            color: white !important;
            border-radius: 12px;
            padding: 10px;
        }
        [data-testid="stChatMessage"][aria-label="Chat message from assistant"] {
            background-color: #4b0082 !important;
            color: white !important;
            border-radius: 12px;
            padding: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

st.title("My AI Chatbot")

# --- FILE ATTACHMENT SECTION ---
uploaded_file = st.file_uploader("Attach a file (Image, TXT):", type=["png", "jpg", "jpeg", "txt"])
file_context = ""

if uploaded_file is not None:
    if uploaded_file.type.startswith("image/"):
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        file_context = f"\n[User attached an image named {uploaded_file.name}]"
    elif uploaded_file.type == "text/plain":
        file_text = uploaded_file.read().decode("utf-8")
        file_context = f"\n[Attached file content:\n{file_text}]"

# Connect to Groq API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
system_instruction = {"role": "system", "content": "You are a friendly, helpful AI assistant."}

active_messages = st.session_state.chats[st.session_state.current_chat]

# --- DISPLAY MESSAGES ---
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
                if st.button("Delete message", key=f"del_msg_{idx}"):
                    active_messages.pop(idx)
                    st.rerun()

# --- HANDLE INPUT ---
if prompt := st.chat_input("Ask me anything..."):
    full_prompt = prompt + file_context
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
    st.rerun()
