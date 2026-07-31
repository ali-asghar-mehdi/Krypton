import streamlit as st
from groq import Groq

st.title("My AI Chatbot")

# Connect using the Groq API key from secrets
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Handle user input
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Get response from AI model (Llama 3)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    )
    
    bot_reply = response.choices[0].message.content

    with st.chat_message("assistant"):
        st.write(bot_reply)
        
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
