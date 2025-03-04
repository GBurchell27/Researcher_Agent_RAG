import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000"

def render_chat_interface():
    """
    Renders the main chat interface
    """
    st.subheader("Chat with your documents")
    
    # Display chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history (if any)
        if st.session_state['chat_history']:
            for i, message in enumerate(st.session_state['chat_history']):
                role = message['role']
                content = message['content']
                
                if role == 'user':
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end;">
                        <div style="background-color: #e6f7ff; padding: 10px; border-radius: 10px; max-width: 80%;">
                            <p><strong>You:</strong> {content}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-start;">
                        <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px; max-width: 80%;">
                            <p><strong>Assistant:</strong> {content}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No messages yet. Start asking questions about your documents!")
    
    # User input for the chat
    st.markdown("### Ask a question")
    
    # Initialize input text in session state if it doesn't exist
    if 'user_input' not in st.session_state:
        st.session_state['user_input'] = ""
    
    # Create different input widgets with unique keys based on state
    if not st.session_state['uploaded_files']:
        st.warning("Please upload a document first to start the conversation.")
        st.text_input(
            "Your question:", 
            value="", 
            disabled=True,
            key="disabled_input"
        )
        st.button("Send", disabled=True, key="disabled_send_btn")
    else:
        # Use a callback to update session state
        def on_input_change():
            st.session_state['user_input'] = st.session_state['enabled_input']
        
        user_input = st.text_input(
            "Your question:",
            key="enabled_input",
            on_change=on_input_change
        )
        
        send_button = st.button("Send", key="send_btn")
        
        if send_button and st.session_state['user_input']:
            user_msg = st.session_state['user_input']
            
            # Add user message to chat history
            st.session_state['chat_history'].append({
                'role': 'user',
                'content': user_msg
            })
            
            # Clear input field
            st.session_state['user_input'] = ""
            
            # Attempt to get response from API
            with st.spinner("Thinking..."):
                try:
                    # Make API call to get the response
                    print(f"Sending query: {user_msg}")
                    
                    # Create the payload
                    payload = {
                        "query": user_msg,
                        "document_id": st.session_state.get('current_document_id', '')
                    }
                    print(f"Payload: {payload}")
                    
                    response = requests.post(
                        f"{API_BASE_URL}/query",
                        json=payload,
                        timeout=10
                    )
                    
                    print(f"Response status: {response.status_code}")
                    if response.status_code != 200:
                        print(f"Error response: {response.text}")
                    
                    if response.status_code == 200:
                        # Success - extract the response
                        try:
                            response_data = response.json()
                            ai_response = response_data.get("response", "No response field found in API response.")
                        except:
                            ai_response = "Received response but couldn't parse JSON."
                    else:
                        # Error from the API
                        ai_response = f"Error from API: Status code {response.status_code}"
                
                except requests.exceptions.ConnectionError:
                    # Connection error (API not available)
                    ai_response = """⚠️ Could not connect to the backend API. 
                    
This is a placeholder response since the API is not available. In a real implementation, I would search through the document for relevant information and generate a meaningful answer based on the content."""
                
                except Exception as e:
                    # Other errors
                    ai_response = f"⚠️ Error: {str(e)}"
            
            # Add AI response to chat history
            st.session_state['chat_history'].append({
                'role': 'assistant',
                'content': ai_response
            })
            
            # Rerun to show the updated chat
            st.rerun()