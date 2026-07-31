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

# Helper for audio
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
        /* Main background */
        .stApp {
            background-color: #000000 !important;
            color: #ffffff !important;
        }
        /* Sidebar background */
        [data-testid="stSidebar"] {
            background-color: #111111 !important;
        }
        /* User chat bubble - Dark Blue */
