import streamlit as st
import google.generativeai as genai

st.title("My AI Chatbot")

# 1. Connect your API key (stored safely in Streamlit Secrets)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Keep track of memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. Show past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 4. Handle user typing
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 5. Get answer from real AI
    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        st.write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
