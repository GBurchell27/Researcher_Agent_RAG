# Helper components for UI layout (buttons, text boxes, etc.)

import streamlit as st
import io
import requests
import json

# API configuration
API_BASE_URL = "http://localhost:8000"

def render_pdf_upload():
    """
    Renders the PDF upload component in the sidebar
    """
    uploaded_file = st.file_uploader(
        "Upload PDF Document", 
        type="pdf",
        help="Upload a PDF document to analyze",
        key="pdf_uploader"
    )
    
    if uploaded_file is not None:
        # Display file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB",
            "File type": uploaded_file.type
        }
        
        st.write("File Details:")
        for key, value in file_details.items():
            st.write(f"- {key}: {value}")
        
        # Process button for the PDF
        if st.button("Process Document", key="process_btn"):
            # Process the PDF with the backend API
            with st.spinner("Processing document..."):
                try:
                    # Prepare the file for upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    
                    # Try to communicate with the backend API
                    response = requests.post(
                        f"{API_BASE_URL}/upload",
                        files=files,
                        timeout=10
                    )
                    
                    # Handle the response
                    if response.status_code == 200:
                        # Success - add to session state
                        if uploaded_file.name not in st.session_state['uploaded_files']:
                            st.session_state['uploaded_files'].append(uploaded_file.name)
                        
                        # Display success message with response details
                        st.success(f"Document '{uploaded_file.name}' processed successfully!")
                        try:
                            response_data = response.json()
                            st.json(response_data)
                        except:
                            st.write("Response received but not in JSON format.")
                    else:
                        # Error from the API
                        st.error(f"Error processing document: API returned status code {response.status_code}")
                        try:
                            response_data = response.json()
                            st.json(response_data)
                        except:
                            st.write(f"Error details: {response.text}")
                
                except requests.exceptions.ConnectionError:
                    # Connection error (API not available)
                    st.error("⚠️ Could not connect to the backend API (connection refused)")
                    st.info("Adding document to local state for testing purposes.")
                    
                    # For testing: still add to session state even if API fails
                    if uploaded_file.name not in st.session_state['uploaded_files']:
                        st.session_state['uploaded_files'].append(uploaded_file.name)
                    
                    st.success(f"Document '{uploaded_file.name}' added to local state (test mode).")
                    
                except Exception as e:
                    # Other errors
                    st.error(f"⚠️ Error: {str(e)}")

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
                    response = requests.post(
                        f"{API_BASE_URL}/query",
                        json={"query": user_msg},
                        timeout=10
                    )
                    
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
            st.experimental_rerun()

def render_document_preview(pdf_file):
    """
    Placeholder for document preview functionality
    """
    st.subheader("Document Preview")
    st.info("Document preview will be implemented in a future update.")
    
    # In the future, this will show a preview of the PDF
    # For now, just show basic information
    st.write(f"Document: {pdf_file.name}")
    st.write(f"Size: {pdf_file.size / 1024:.2f} KB")