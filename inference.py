from pathlib import Path
import streamlit as st
from ingress import ingress_file_doc


def process_files_and_links(files, web_links, section):
    with st.spinner("Processing..."):
        for uploaded_file in files:
            process_file(uploaded_file, section, web_links)  # ✅ Call function directly
    st.session_state["files_processed"] = True

def process_file(uploaded_file, section, web_links):
    try:
        file_name = uploaded_file.name
        st.session_state["file_name"] = file_name
        # Use pathlib to define the file path
        temp_dir = Path("./temp_files")
        temp_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        
        # Define the file path
        file_path = temp_dir / file_name  # Concatenate the directory path and file name

        # Save file locally for processing
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())


        # Call the function with correct arguments
        response = ingress_file_doc(file_name, file_path, web_links, section)

        if "error" in response:
            st.error(f"Error processing file: {response['error']}")
        else:
            st.success(f"File '{file_name}' processed successfully!")

    except Exception as e:
        st.error(f"Connection error: {e}")
        
        
        

