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

# --- FIXED DARK MODE STYLING ---
if dark_mode:
    st.markdown(
        """
        <style>
        /* Whole App Background */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #000000 !important;
            color: #ffffff !important;
        }
        /* Sidebar Background */
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background-color: #111111 !important;
        }
        /* All Text Color */
        h1, h2, h3, p, span, label {
            color: #ffffff !important;
        }
        /* User Chat Message Container (Dark Blue) */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background-color: #002b49 !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        /* AI Chat Message Container (Purple) */
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

# --- FILE ATTACHMENT SECTION ---
uploaded_file = st.file_uploader("Attach a file (Image, TXT):", type=
