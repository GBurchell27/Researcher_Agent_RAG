# Streamlit app entry point (UI logic)
import streamlit as st
import requests
import json
from ui_components import render_chat_interface, render_pdf_upload

# Page configuration
st.set_page_config(
    page_title="Research Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom styling
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stSidebar .sidebar-content {
        padding: 1rem;
    }
    .chat-container {
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize all session state variables
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'uploaded_files' not in st.session_state:
    st.session_state['uploaded_files'] = []
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""

def main():
    # App header
    st.title("Research Assistant")
    st.markdown("Upload PDFs and chat with your documents to extract insights.")
    
    # Sidebar - PDF Upload Section
    with st.sidebar:
        st.header("Document Management")
        render_pdf_upload()
        
        # Display uploaded files (placeholder)
        if st.session_state['uploaded_files']:
            st.subheader("Uploaded Documents")
            for file in st.session_state['uploaded_files']:
                st.write(f"📄 {file}")
        else:
            st.info("No documents uploaded yet. Upload a PDF to get started.")
        
        # Placeholder for API connection status
        st.sidebar.markdown("---")
        st.sidebar.subheader("System Status")
        try:
            # Placeholder for API health check
            api_status = "🟢 Connected"
            # In the future, this will make a real API call to check status
            # response = requests.get("http://localhost:8000/health")
            # if response.status_code == 200:
            #     api_status = "🟢 Connected"
            # else:
            #     api_status = "🔴 Disconnected"
        except Exception as e:
            api_status = "🔴 Disconnected"
        
        st.sidebar.markdown(f"Backend API: {api_status}")
    
    # Main content area - Chat Interface
    render_chat_interface()

if __name__ == "__main__":
    main()