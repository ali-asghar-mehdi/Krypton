import streamlit as st
from groq import Groq
from gtts import gTTS
import io
from PIL import Image

st.set_page_config(page_title="My AI Chatbot", layout="wide")

# Connect to Groq API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
system_instruction = {"role": "system", "content": "You are a friendly, helpful AI assistant."}

# Initialize chat storage
if "chats" not in st.session_state:
    st.session_state.chats = {"New Chat": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat"

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

# Helper function for audio
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
                        if st.session_state.current_chat == chat_name:
                            st.session_state.current_chat = new_name
                        st.rerun()

        with col_del:
            if len(st.session_state.chats) > 1:
