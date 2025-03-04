import streamlit as st
import requests

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
                        timeout=30  # Increased timeout for PDF processing
                    )
                    
                    # Handle the response
                    if response.status_code == 200:
                        # Success - add to session state
                        if uploaded_file.name not in st.session_state['uploaded_files']:
                            st.session_state['uploaded_files'].append(uploaded_file.name)
                        
                        # Get the response data
                        response_data = response.json()
                        
                        # Store document ID in session state
                        if 'document_id' in response_data:
                            st.session_state['current_document_id'] = response_data['document_id']
                            st.session_state['current_document_name'] = uploaded_file.name
                            print(f"Set document ID: {response_data['document_id']}")
                        
                        # Store document statistics in session state
                        if 'document_stats' not in st.session_state:
                            st.session_state['document_stats'] = {}
                        
                        if 'statistics' in response_data:
                            st.session_state['document_stats'][uploaded_file.name] = response_data['statistics']
                        
                        # Store sample chunks in session state
                        if 'document_samples' not in st.session_state:
                            st.session_state['document_samples'] = {}
                        
                        if 'sample_chunks' in response_data:
                            st.session_state['document_samples'][uploaded_file.name] = response_data['sample_chunks']
                        
                        # Display success message
                        st.success(f"Document '{uploaded_file.name}' processed successfully!")
                        
                        # Display document statistics
                        if 'statistics' in response_data:
                            stats = response_data['statistics']
                            st.subheader("Document Statistics")
                            stats_col1, stats_col2 = st.columns(2)
                            with stats_col1:
                                st.metric("Pages", stats.get('total_pages', 0))
                                st.metric("Text Chunks", stats.get('total_chunks', 0))
                            with stats_col2:
                                st.metric("Characters", f"{stats.get('total_characters', 0):,}")
                                st.metric("Est. Tokens", f"{stats.get('estimated_tokens', 0):,}")
                        
                        # Display sample chunks
                        if 'sample_chunks' in response_data and response_data['sample_chunks']:
                            st.subheader("Sample Content")
                            
                            # Create tabs for each preview instead of expanders
                            preview_tabs = st.tabs([
                                f"Page {chunk.get('page', 'N/A')} - Preview {idx+1}" 
                                for idx, chunk in enumerate(response_data['sample_chunks'])
                            ])
                            
                            # Display content in each tab
                            for idx, tab in enumerate(preview_tabs):
                                if idx < len(response_data['sample_chunks']):
                                    chunk = response_data['sample_chunks'][idx]
                                    with tab:
                                        st.text(chunk.get('text_preview', 'No preview available'))
                    else:
                        # Error from the API
                        st.error(f"Error processing document: API returned status code {response.status_code}")
                        try:
                            response_data = response.json()
                            if 'detail' in response_data:
                                st.error(f"Error details: {response_data['detail']}")
                            else:
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