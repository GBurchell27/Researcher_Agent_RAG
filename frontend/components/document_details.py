import streamlit as st

API_BASE_URL = "http://localhost:8000"

def render_document_details():
    """
    Render details about processed documents
    """
    if not st.session_state['uploaded_files']:
        return
    
    st.subheader("Processed Documents")
    
    for doc_name in st.session_state['uploaded_files']:
        with st.expander(f"📄 {doc_name}"):
            # Show statistics if available
            if 'document_stats' in st.session_state and doc_name in st.session_state['document_stats']:
                stats = st.session_state['document_stats'][doc_name]
                cols = st.columns(4)
                cols[0].metric("Pages", stats.get('total_pages', 'N/A'))
                cols[1].metric("Chunks", stats.get('total_chunks', 'N/A'))
                cols[2].metric("Characters", f"{stats.get('total_characters', 0):,}")
                cols[3].metric("Est. Tokens", f"{stats.get('estimated_tokens', 0):,}")
            else:
                st.info("No detailed statistics available for this document.")
            
            # Show sample chunks if available - using tabs instead of nested expanders
            if 'document_samples' in st.session_state and doc_name in st.session_state['document_samples']:
                st.write("Content Samples:")
                
                # Create tabs for each preview instead of nested expanders
                if st.session_state['document_samples'][doc_name]:
                    preview_tabs = st.tabs([
                        f"Page {chunk.get('page', 'N/A')} - Preview {idx+1}" 
                        for idx, chunk in enumerate(st.session_state['document_samples'][doc_name])
                    ])
                    
                    # Display content in each tab
                    for idx, tab in enumerate(preview_tabs):
                        if idx < len(st.session_state['document_samples'][doc_name]):
                            chunk = st.session_state['document_samples'][doc_name][idx]
                            with tab:
                                st.text(chunk.get('text_preview', 'No preview available'))
                else:
                    st.info("No sample content available.")
            
            # Add a button to remove the document
            if st.button(f"Remove Document", key=f"remove_{doc_name}"):
                st.session_state['uploaded_files'].remove(doc_name)
                if 'document_stats' in st.session_state and doc_name in st.session_state['document_stats']:
                    del st.session_state['document_stats'][doc_name]
                if 'document_samples' in st.session_state and doc_name in st.session_state['document_samples']:
                    del st.session_state['document_samples'][doc_name]
                st.experimental_rerun()