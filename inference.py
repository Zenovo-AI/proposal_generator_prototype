from pathlib import Path
import time
import streamlit as st
from ingress import ingress_file_doc


from concurrent.futures import ThreadPoolExecutor

def process_files_and_links(files, web_links, section):
    with st.spinner("Processing..."):
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_file, file, section, web_links) for file in files]
            for future in futures:
                future.result()  # ✅ Call function directly
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
        try:
            response = ingress_file_doc(file_name, file_path, web_links or [], section)
            if "error" in response:
                st.error(f"File processing error: {response['error']}")
            else:
                placeholder = st.empty()
                placeholder.success(f"File '{file_name}' processed successfully!")
                time.sleep(5)
                placeholder.empty()
        except Exception as e:
            st.error(f"Unexpected error: {e}")

    except Exception as e:
        st.error(f"Connection error: {e}")

