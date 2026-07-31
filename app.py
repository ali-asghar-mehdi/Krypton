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

active_messages = st.session_state.chats[st.session_state.current_chat]

# --- SIDEBAR: Chat Sessions, Renaming, & Rewind ---
with st.sidebar:
    st.header("Chat Sessions")
    
    # Button to start a new conversation
    if st.button("+ New Chat", type="primary"):
        new_id = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[new_id] = []
        st.session_state.current_chat = new_id
        st.rerun()

    st.divider()
    
    # List all chat sessions with Select, Rename, and Delete buttons
    chat_names = list(st.session_state.chats.keys())
    for chat_name in chat_names:
        col_select, col_edit, col_del = st.columns([3, 1, 1])
        
        # Select Chat
        with col_select:
            if st.button(chat_name, key=f"select_{chat_name}"):
                st.session_state.current_chat = chat_name
                st.rerun()
                
        # Rename Chat
        with col_edit:
            with st.popover("✏️"):
                new_name = st.text_input("New Chat Name:", value=chat_name, key=f"rename_{chat_name}")
                if st.button("Save", key=f"save_{chat_name}"):
                    if new_name and new_name != chat_name:
                        st.session_state.chats[new_name] = st.session_state.chats.pop(chat_name)
                        if st.session_state.current_chat == chat_name:
                            st.session_state.current_chat = new_name
                        st.rerun()

        # Delete Chat
        with col_del:
            if len(st.session_state.chats) > 1:
                if st.button("🗑️", key=f"del_{chat_name}"):
                    del st.session_state.chats[chat_name]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

    st.divider()
    st.header("⏪ Rewind Chat")
    st.caption("Click to go back to any message:")
    
    # Sidebar Rewind buttons for current chat
    for idx, msg in enumerate(active_messages):
        role_label = "You" if msg["role"] == "user" else "AI"
        preview = msg["content"][:18] + "..." if len(msg["content"]) > 18 else msg["content"]
        if st.button(f"[{role_label}] {preview}", key=f"side_rewind_{idx}"):
            st.session_state.chats[st.session_state.current_chat] = active_messages[:idx + 1]
            st.rerun()

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

# --- DISPLAY MESSAGES & IN-LINE REWIND OPTIONS ---
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
                # Edit and resend option for user messages
                if message["role"] == "user":
                    new_text = st.text_input("Edit message:", value=message["content"], key=f"edit_input_{idx}")
                    if st.button("Save & Resend", key=f"save_edit_{idx}"):
                        # Truncate to before this message, then add new edited prompt
                        st.session_state.chats[st.session_state.current_chat] = active_messages[:idx]
                        st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": new_text})
                        st.rerun()
                
                # Rewind button for any message
                if st.button("⏪ Rewind to here (delete newer messages)", key=f"rewind_msg_{idx}"):
                    st.session_state.chats[st.session_state.current_chat] = active_messages[:idx + 1]
                    st.rerun()

                if st.button("🗑️ Delete this message", key=f"del_msg_{idx}"):
                    active_messages.pop(idx)
                    st.rerun()

# --- HANDLE NEW USER INPUT ---
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
