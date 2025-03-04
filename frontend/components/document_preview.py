import streamlit as st

API_BASE_URL = "http://localhost:8000"
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