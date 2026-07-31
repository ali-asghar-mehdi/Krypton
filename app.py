# --- SIDEBAR: Chat Sessions & Renaming ---
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
        
        # 1. Select Chat Button
        with col_select:
            if st.button(chat_name, key=f"select_{chat_name}"):
                st.session_state.current_chat = chat_name
                st.rerun()
                
        # 2. Rename Chat Button (Opens a small menu)
        with col_edit:
            with st.popover("✏️"):
                new_name = st.text_input("New Chat Name:", value=chat_name, key=f"rename_input_{chat_name}")
                if st.button("Save", key=f"save_name_{chat_name}"):
                    if new_name and new_name != chat_name:
                        # Move saved messages to the new name key
                        st.session_state.chats[new_name] = st.session_state.chats.pop(chat_name)
                        if st.session_state.current_chat == chat_name:
                            st.session_state.current_chat = new_name
                        st.rerun()

        # 3. Delete Chat Button
        with col_del:
            if len(st.session_state.chats) > 1:
                if st.button("🗑️", key=f"del_{chat_name}"):
                    del st.session_state.chats[chat_name]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()
