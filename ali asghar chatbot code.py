import streamlit as st

st.title("My AI Chatbot")

# 1. Initialize chat history in session memory
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Display previous messages from memory
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 3. Get new user input
if user_prompt := st.chat_input("Type your message here..."):
    # Display user's message in the app
    with st.chat_message("user"):
        st.write(user_prompt)
    
    # Save user's message to memory
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Generate bot response (Replace this text with an actual AI model!)
    bot_response = f"You said: {user_prompt}"

    # Display bot's message in the app
    with st.chat_message("assistant"):
        st.write(bot_response)

    # Save bot's message to memory
    st.session_state.messages.append({"role": "assistant", "content": bot_response})