import streamlit as st
from groq import Groq
from gtts import gTTS
import io

st.set_page_config(page_title="My AI Chatbot", layout="wide")
st.title("My AI Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Helper function to convert text to voice audio
def get_voice_audio(text):
    tts = gTTS(text=text, lang='en', tld='co.uk')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# --- SIDEBAR: Chat History & Rewind Menu ---
with st.sidebar:
    st.header("Chat History & Rewind")
    if st.button("Start Fresh Chat", type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.write("**Rewind Chat to Any Point:**")
    
    # List all previous messages in sidebar
    for idx, msg in enumerate(st.session_state.messages):
        role_label = "You" if msg["role"] == "user" else "AI"
        preview = msg["content"][:20] + "..." if len(msg["content"]) > 20 else msg["content"]
        
        if st.button(f" Rewind to: [{role_label}] {preview}", key=f"side_rewind_{idx}"):
            st.session_state.messages = st.session_state.messages[:idx+1]
            st.rerun()

# Connect to Groq API key
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- DISPLAY CHAT MESSAGES ---
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            # Button to play audio on demand
            if st.button("🔊 Play Voice", key=f"voice_{idx}"):
                audio_data = get_voice_audio(message["content"])
                st.audio(audio_data, format="audio/mp3", autoplay=True)
                
        with col2:
            # Options menu under each message
            with st.expander("⚙️ Options"):
                if message["role"] == "user":
                    new_text = st.text_input("Edit message:", value=message["content"], key=f"edit_{idx}")
                    if st.button("Save & Resend", key=f"save_{idx}"):
                        st.session_state.messages = st.session_state.messages[:idx]
                        st.session_state.messages.append({"role": "user", "content": new_text})
                        st.rerun()
                
                if st.button("Delete newer messages", key=f"rewind_opt_{idx}"):
                    st.session_state.messages = st.session_state.messages[:idx+1]
                    st.rerun()

# --- HANDLE NEW USER INPUT ---
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get response from AI model
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    )
    
    bot_reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    st.rerun()
