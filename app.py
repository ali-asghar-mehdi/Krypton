import streamlit as st
from groq import Groq
from gtts import gTTS
import io

st.set_page_config(page_title="My AI Chatbot", layout="wide")
st.title("My AI Chatbot")

# Initialize session state for message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Function to generate voice audio bytes
def speak_text(text):
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# --- SIDEBAR: History & Rewind ---
with st.sidebar:
    st.header("Chat History & Rewind")
    if st.button("Start Fresh Chat", type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.write("**Rewind to a Previous Message:**")
    
    # List each user message with a Rewind button
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            preview = msg["content"][:25] + "..." if len(msg["content"]) > 25 else msg["content"]
            if st.button(f" Rewind to: {preview}", key=f"rewind_{idx}"):
                # Keep messages up to this user message
                st.session_state.messages = st.session_state.messages[:idx]
                st.rerun()

# Connect to Groq API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- DISPLAY CHAT MESSAGES ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # Options menu for user messages (Edit & Rewind)
        if message["role"] == "user":
            with st.expander("Options"):
                new_text = st.text_input("Edit message:", value=message["content"], key=f"edit_input_{idx}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(" Save & Rerun", key=f"save_{idx}"):
                        st.session_state.messages = st.session_state.messages[:idx]
                        st.session_state.messages.append({"role": "user", "content": new_text})
                        st.rerun()
                with col2:
                    if st.button(" Delete from here", key=f"del_{idx}"):
                        st.session_state.messages = st.session_state.messages[:idx]
                        st.rerun()

# --- HANDLE NEW USER INPUT ---
if prompt := st.chat_input("Ask me anything..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Get response from AI
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    )
    
    bot_reply = response.choices[0].message.content

    # Show bot response and play voice
    with st.chat_message("assistant"):
        st.write(bot_reply)
        # Voice output
        audio_fp = speak_text(bot_reply)
        st.audio(audio_fp, format="audio/mp3", autoplay=True)
        
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
