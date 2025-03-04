# Streamlit app entry point (UI logic)
import streamlit as st
import requests
import json
from components import render_pdf_upload, render_document_details, render_chat_interface

API_BASE_URL = "http://localhost:8000"

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
if 'document_stats' not in st.session_state:
    st.session_state['document_stats'] = {}
if 'document_samples' not in st.session_state:
    st.session_state['document_samples'] = {}
if 'api_status' not in st.session_state:
    st.session_state['api_status'] = "unknown"
if 'api_response' not in st.session_state:
    st.session_state['api_response'] = None
if 'api_error' not in st.session_state:
    st.session_state['api_error'] = None

# API configuration
API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """Check if the FastAPI backend is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            st.session_state['api_status'] = "connected"
            st.session_state['api_response'] = response.json()
            st.session_state['api_error'] = None
            return True
        else:
            st.session_state['api_status'] = "error"
            st.session_state['api_response'] = {"status_code": response.status_code}
            st.session_state['api_error'] = f"API returned status code {response.status_code}"
            return False
    except requests.exceptions.ConnectionError:
        st.session_state['api_status'] = "disconnected"
        st.session_state['api_response'] = None
        st.session_state['api_error'] = "Could not connect to the API (connection refused)"
        return False
    except Exception as e:
        st.session_state['api_status'] = "error"
        st.session_state['api_response'] = None
        st.session_state['api_error'] = str(e)
        return False

def test_api_connection():
    """Test connection to the API and update session state"""
    if check_api_health():
        st.success("✅ Successfully connected to FastAPI backend!")
    else:
        st.error("❌ Failed to connect to FastAPI backend.")

def main():
    # App header
    st.title("Research Assistant")
    st.markdown("Upload PDFs and chat with your documents to extract insights.")
    
    # Sidebar - PDF Upload Section
    with st.sidebar:
        st.header("Document Management")
        render_pdf_upload()
        
        # Display uploaded files with details
        if st.session_state['uploaded_files']:
            render_document_details()
        else:
            st.info("No documents uploaded yet. Upload a PDF to get started.")
        
        # API connection status
        st.sidebar.markdown("---")
        st.sidebar.subheader("Backend Connection")
        
        # Check API status
        if st.session_state['api_status'] == "unknown":
            # Initial check only once at startup
            check_api_health()
        
        # Display current status
        if st.session_state['api_status'] == "connected":
            st.sidebar.markdown("Status: 🟢 Connected")
        elif st.session_state['api_status'] == "disconnected":
            st.sidebar.markdown("Status: 🔴 Disconnected")
        elif st.session_state['api_status'] == "error":
            st.sidebar.markdown("Status: 🟠 Error")
        else:
            st.sidebar.markdown("Status: ⚪ Unknown")
        
        # Test connection button
        if st.sidebar.button("Test Connection", key="test_conn_btn"):
            test_api_connection()
        
        # Show response details if available
        if st.session_state['api_status'] != "unknown":
            st.sidebar.markdown("---")
            st.sidebar.subheader("Connection Details")
            
            if st.session_state['api_response']:
                st.sidebar.json(st.session_state['api_response'])
            
            if st.session_state['api_error']:
                st.sidebar.error(st.session_state['api_error'])
    
    # Main content area - Chat Interface
    render_chat_interface()

if __name__ == "__main__":
    main()