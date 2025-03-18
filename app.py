import json
import logging
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
import traceback
import numpy as np
import streamlit as st
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete, gpt_4o_complete
from langchain_openai import OpenAI
from lightrag.utils import EmbeddingFunc
from constant import SECTION_KEYWORDS, select_section
from db_helper import check_if_file_exists_in_section, check_working_directory, delete_file, get_uploaded_sections, initialize_database
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from inference import process_files_and_links
from google_drive_helper import GoogleDriveHelper
from google_docs_helper import GoogleDocsHelper, GoogleDriveAPI
from auth import auth_flow, logout, validate_session
from utils import clean_text, get_folder_id_from_url

def initialize_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "initialized" not in st.session_state:
        initialize_database()
        st.session_state.initialized = True
    if "proposal_text" not in st.session_state: 
        st.session_state.proposal_text = ""
    if "google_drive_authenticated" not in st.session_state:
        st.session_state.google_drive_authenticated = False
    if "show_gdrive_form" not in st.session_state:
        st.session_state.show_gdrive_form = False
    if "google_drive_link" not in st.session_state:
        st.session_state.google_drive_link = ""
    if "pdf_file_name" not in st.session_state:
        st.session_state.pdf_file_name = ""
    if "show_gdocs_form" not in st.session_state:
        st.session_state.show_gdocs_form = False
    if "doc_file_name" not in st.session_state:
        st.session_state.doc_file_name = ""
    if "proposal_text" not in st.session_state:
        st.session_state.proposal_text = ""
    if "upload_triggered" not in st.session_state:
        st.session_state.upload_triggered = False


auth_cache_dir = Path(__file__).parent / "auth_cache"
auth_cache_dir.mkdir(exist_ok=True, parents=True)

client_secret_path = auth_cache_dir / "client_secret.json"
auth_status_path = auth_cache_dir / "auth_success.txt"
credentials_path = auth_cache_dir / "credentials.json"


# Helper Function to Clean and Parse JSON
def clean_and_parse_json(raw_json):
    try:
        fixed_json = raw_json.replace("{{", "{").replace("}}", "}")
        return json.loads(fixed_json)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}. Raw data: {raw_json}")
        return None


def embedding_func(texts: list[str]) -> np.ndarray:
    embeddings = openai_embed(
        texts,
        model="text-embedding-3-large",
        api_key=st.secrets["OPENAI_API_KEY"],
        base_url=None
    )
    if embeddings is None:
        logging.error("Received empty embeddings from API.")
        return np.array([])
    return embeddings


class RAGFactory:
    _shared_embedding = EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=embedding_func
    )

    @classmethod
    def create_rag(cls, working_dir: str) -> LightRAG:
        """Create a LightRAG instance with shared configuration, upload to GCS if specified"""
        return LightRAG(
            working_dir=working_dir,
            addon_params={
                "insert_batch_size": 10  # Process 10 documents per batch
            },
            llm_model_func=gpt_4o_complete,
            embedding_func=cls._shared_embedding
        )



def generate_explicit_query(query):
    """Expands the user query and merges expanded queries into a single, explicit query."""
    llm = OpenAI(temperature=0)

    prompt = f"""
    Given the following vague query:

    '{query}'

    Expand this query into **seven structured subqueries** that break down the proposal into detailed components.
    Ensure that the query includes **specific details** such as:
    - The sender's company name, address, email, and phone number.
    - The recipient’s name, position, organization, and address.
    - A structured breakdown of the proposal, including scope of work, compliance, pricing, experience, and additional documents.

    Example:

    **Original Query:** "Can you write a proposal based on the requirements in the RFQ?"

    **Expanded Queries:**
    1. "Provide a formal header section with the sender's full company details (name, address, email, phone) and the recipient's details (name, position, organization, address)."
    2. "Write a professional opening paragraph that introduces the company and states the purpose of the proposal."
    3. "Describe the scope of work, breaking it into detailed sections for each service category (e.g., borehole rehabilitation and new drilling)."
    4. "Provide a clear breakdown of pricing, including cost per lot and total project cost, specifying currency and payment terms."
    5. "Outline a detailed project plan and timeline, including key milestones and deliverables."
    6. "List all required compliance details, including adherence to RFQ terms, delivery timelines, insurance coverage, and taxation requirements."
    7. "Outline the company's experience and qualifications, listing past projects, certifications, and key personnel expertise."
    8. "List all necessary additional documents, such as bidder’s statement, vendor profile form, and statement of confirmation."

    **Final Explicit Query:**  
    "Can you write a proposal based on the requirements in the RFQ, including:  
    (1) A formal header with sender and recipient details,  
    (2) An introduction stating the company’s expertise and purpose of the proposal,  
    (3) A detailed scope of work for each service component,  
    (4) A structured pricing breakdown with currency and payment terms,  
    (5) A detailed project plan and timeline with milestones, and
    (6) A section on compliance, including delivery, insurance, and taxation,  
    (7) A section on experience and qualifications, highlighting past projects and key personnel, and  
    (8) A section listing all required additional documents."

    Now, generate an explicit query for:

    '{query}'
    """

    response = llm.invoke(prompt)
    return response.strip()




# def generate_answer():
#     """Generates an answer when the user enters a query and presses Enter."""
#     query = st.session_state.query_input  # Get user query from session state
#     if not query:
#         return  # Do nothing if query is empty

#     with st.spinner("Generating answer..."):
#         try:
#             working_dir = Path("./analysis_workspace")
#             working_dir.mkdir(parents=True, exist_ok=True)
#             rag = RAGFactory.create_rag(str(working_dir))  
#             response = rag.query(query, QueryParam(mode=st.session_state.search_mode))

#             # Store in chat history
#             st.session_state.chat_history.append(("You", query))
#             st.session_state.chat_history.append(("Bot", response))
#         except Exception as e:
#             st.error(f"Error retrieving response: {e}")

#     # Reset query input to allow further queries
#     st.session_state.query_input = ""


def generate_answer():
    """Generates an answer when the user enters a query and presses Enter."""
    query = st.session_state.query_input  # Get user query from session state
    if not query:
        return  # Do nothing if query is empty

    with st.spinner("Expanding query..."):
        expanded_queries = generate_explicit_query(query)

    with st.spinner("Generating answer..."):
        try:
            working_dir = Path("./analysis_workspace")
            working_dir.mkdir(parents=True, exist_ok=True)
            rag = RAGFactory.create_rag(str(working_dir))  

            # Send combined query to RAG
            response = rag.query(expanded_queries, QueryParam(mode="hybrid"))

            # Store in chat history
            st.session_state.chat_history.append(("You", query))
            st.session_state.chat_history.append(("Bot", response))
            
            # Store response as proposal text
            cleaned_response = clean_text(response)
            st.session_state.proposal_text = cleaned_response
            
        except Exception as e:
            st.error(f"Error retrieving response: {e}")

    # Reset query input to allow further queries
    st.session_state.query_input = ""


def main():
    st.title("Proposal and Chatbot System")
    st.write("Upload a document and ask questions based on structured knowledge retrieval.")
    
    initialize_session_state()
    validate_session()

    # List of sections
    sections = list(SECTION_KEYWORDS.values())

    # Ensure session state has a default section
    if "current_section" not in st.session_state:
        st.session_state.current_section = sections[0]

    # Sidebar: Select section
    selected_section = st.sidebar.selectbox(
        "Select a document section:", 
        options=sections, 
        key="main_nav", 
        index=sections.index(st.session_state.current_section)
    )
    st.session_state.current_section = selected_section

    # Get section and table name
    section, table_name = select_section(selected_section)

    # File uploader widget
    files = st.sidebar.file_uploader("Upload documents", accept_multiple_files=True, type=["pdf", "txt"])

    # Store uploaded file name in session state
    for file in files:
        st.session_state["file_name"] = file.name

    # Web links input
    web_links = st.sidebar.text_area("Enter web links (one per line)", key="web_links")

    # Ensure files_processed is in session state
    if "files_processed" not in st.session_state:
        st.session_state["files_processed"] = False

    # Sidebar: Retrieval mode selection
    # st.session_state.search_mode = st.sidebar.selectbox("Select retrieval mode", ["local", "global", "hybrid", "mix"], key="mode_selection")

    # Process files and links if present
    if (files or web_links) and not st.session_state["files_processed"]:
        for file in files:
            file_name = file.name

            # Check if file exists in database or working directory
            file_in_db = check_if_file_exists_in_section(file_name, section)
            dir_exists = check_working_directory(file_name, section)

            if file_in_db and dir_exists:
                placeholder = st.empty()
                placeholder.warning(f"The file '{file_name}' has already been processed and exists in the '{section}' section.")
                time.sleep(5)
                placeholder.empty()
            else:
                placeholder = st.empty()
                placeholder.write("🔄 Processing files and links...")
                time.sleep(5)
                placeholder.empty()

                # Process the files and links
                process_files_and_links(files, web_links, section)  

                placeholder.write("✅ Files and links processed!")
                time.sleep(5)  
                placeholder.empty()


    # Reset processing state and delete working directory
    if st.sidebar.button("Reset Processing", key="reset"):
        # Clear session state except for initialized state
        keys_to_keep = {"initialized"}
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]

        # Reset processing flag
        st.session_state["files_processed"] = False

        # Define the working directory
        working_dir = Path("./analysis_workspace")

        # Delete the working directory if it exists
        if working_dir.exists() and working_dir.is_dir():
            import shutil
            shutil.rmtree(working_dir)
            st.sidebar.success("Processing reset! The working directory has been deleted.")
        else:
            st.sidebar.warning("No working directory found to delete.")
    
    # Google Drive section
    if st.sidebar.button("Google Drive"):
        st.session_state.show_gdrive_form = True
        if "drive_service" in st.session_state:
            del st.session_state.drive_service

    if st.session_state.get("show_gdrive_form", False):
        # Authenticate FIRST
        service = auth_flow()
        if not service:
            st.session_state.show_gdrive_form = False
            st.stop()

        # Store service only after successful auth
        st.session_state.drive_service = service

        with st.sidebar:
            with st.form("google_drive_upload_form", clear_on_submit=True):
                st.write("### Google Drive Upload")
                google_drive_link = st.text_input("Root Folder Link:", 
                                                value=st.session_state.get("google_drive_link", ""))
                client_name = st.text_input("Client Name:", 
                                            value=st.session_state.get("client_name", ""))
                pdf_file_name = st.text_input("PDF Name:", 
                                            value=st.session_state.get("pdf_file_name", ""))
                
                submitted = st.form_submit_button("📤 Upload to Google Drive")
                if submitted:
                    st.session_state.update({
                        "google_drive_link": google_drive_link,
                        "client_name": client_name,
                        "pdf_file_name": pdf_file_name,
                        "upload_triggered": True
                    })

    if st.session_state.get("upload_triggered"):
        try:
            st.session_state.upload_triggered = False
            
            # Validate proposal exists
            if not st.session_state.get("proposal_text"):
                st.error("Generate a proposal first!")
                st.stop()

            # Get cached service
            service = st.session_state.drive_service
            
            helper = GoogleDriveHelper(service)

            # Get root folder ID from input
            root_folder_id = get_folder_id_from_url(st.session_state.google_drive_link)

            # Create folder structure
            proposal_folder_id = helper.create_folder("Proposals", parent_folder_id=root_folder_id)
            client_folder_id = helper.create_folder(
                st.session_state.client_name.strip(), 
                parent_folder_id=proposal_folder_id
            )

            # Upload file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                file_link = helper.upload_file(
                    folder_id=client_folder_id,
                    file_path=tmp.name,
                    content=st.session_state.proposal_text,
                    file_name=f"{st.session_state.pdf_file_name}.pdf"
                )

            st.success(f"✅ Upload Successful! [View File]({file_link})")

            # **Clear form values from session state after successful upload**
            keys_to_clear = ["google_drive_link", "client_name", "pdf_file_name", "show_gdrive_form"]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
                
            # Collapse the form
            st.session_state.show_gdocs_form = False
            st.rerun()

        except Exception as e:
            st.error(f"Upload failed: {str(e)}")
            st.error(traceback.format_exc())

    
    # Google Docs Integration    
    if st.sidebar.button("Google Docs"):
        st.session_state.show_gdocs_form = True
        if "docs_service" in st.session_state:
            del st.session_state.docs_service
        if "drive_service" in st.session_state:
            del st.session_state.drive_service
        if "service" in st.session_state:
            del st.session_state.service

    if st.session_state.get("show_gdocs_form", False):
        # Authenticate and get credentials
        credentials_data = auth_flow()
        if not credentials_data or "token" not in credentials_data:
            st.session_state.show_gdocs_form = False
            st.stop()
        
        # Convert credentials data to Credentials object
        try:
            creds = Credentials.from_authorized_user_info(credentials_data['token'])
        except KeyError:
            st.error("Invalid credentials format")
            st.stop()
        
        # Create proper services
        st.session_state.docs_service = build("docs", "v1", credentials=creds)
        st.session_state.drive_service = build("drive", "v3", credentials=creds)

        with st.sidebar:
            with st.form("google_docs_upload_form", clear_on_submit=True):
                st.write("### Google Docs Upload")
                google_drive_link = st.text_input("Root Folder Link:", 
                                                value=st.session_state.get("google_drive_link", ""))
                client_name = st.text_input("Client Name:", 
                                        value=st.session_state.get("client_name", ""))
                doc_file_name = st.text_input("Document Name:", 
                                            value=st.session_state.get("doc_file_name", ""))
                
                submitted = st.form_submit_button("📄 Upload to Google Docs")
                if submitted:
                    st.session_state.update({
                        "google_drive_link": google_drive_link,
                        "client_name": client_name,
                        "doc_file_name": doc_file_name,
                        "upload_triggered": True
                    })
                    
    if st.session_state.get("upload_triggered"):
        try:
            # Validate proposal exists
            if not st.session_state.proposal_text:
                st.error("Generate a proposal first!")
                st.stop()
                
            # Get cached service
            st.session_state.upload_triggered = False

            service = st.session_state.docs_service  # Docs service instance
            service1 = st.session_state.drive_service  # Drive service instance

            docs_helper = GoogleDocsHelper(service)
            drive_helper = GoogleDriveAPI(service1)


            # Get root folder ID from input
            root_folder_id = get_folder_id_from_url(st.session_state.google_drive_link)
            # Ensure root_folder_id is valid
            if not root_folder_id:
                st.error("Invalid Google Drive folder link! Please enter a correct link.")
                st.stop()

            # Create folder structure
            proposal_folder_id = drive_helper.create_folder("Proposals", parent_folder_id=root_folder_id)
            client_folder_id = drive_helper.create_folder(
                st.session_state.client_name.strip(), 
                parent_folder_id=proposal_folder_id
            )

            # Create document
            doc_id = docs_helper.create_document(st.session_state.doc_file_name)
            docs_helper.write_to_document(doc_id, st.session_state.proposal_text)

            # Move document to client folder
            st.session_state.drive_service.files().update(
                fileId=doc_id,
                addParents=client_folder_id,
                removeParents='root' if root_folder_id == 'root' else root_folder_id,
                fields='id, parents'
            ).execute()

            placeholder = st.empty()
            placeholder.success(f"✅ Upload Successful! [View Document](https://docs.google.com/document/d/{doc_id}/view)")
            time.sleep(20)
            placeholder.empty()
            
            # **Clear form values and collapse form after successful upload**
            keys_to_clear = ["google_drive_link", "client_name", "doc_file_name", "show_gdocs_form"]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
                
            # Collapse the form
            st.session_state.show_gdocs_form = False
            st.rerun()

        except Exception as e:
            st.error(f"Upload failed: {str(e)}")
            st.error(traceback.format_exc())
        
            
    # Logout
    if st.sidebar.button("Logout", key="main_logout"):
        st.session_state.force_refresh = True
        logout()


    # Input field with automatic query execution on Enter
    st.text_input("Ask a question about the document:", key="query_input", on_change=generate_answer)

    # Display chat history
    for role, message in st.session_state.chat_history:
        with st.chat_message("user" if role == "You" else "assistant"):
            st.write(message)

    # Sidebar: Uploaded files display
    st.sidebar.write("### Uploaded Files")
    try:
        conn = sqlite3.connect("files.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(f'SELECT file_name FROM "{table_name}";')
        uploaded_files_list = [file[0] for file in cursor.fetchall()]

        if uploaded_files_list:
            for file_name in uploaded_files_list:
                delete_key = f"delete_{table_name}_{file_name}"
                col1, col2 = st.sidebar.columns([3, 1])
                with col1:
                    st.sidebar.write(file_name)
                with col2:
                    if st.sidebar.button("Delete", key=delete_key):
                        try:
                            delete_file(file_name, table_name)
                            st.sidebar.success(f"File '{file_name}' deleted successfully!")
                        except Exception as e:
                            st.error(f"Failed to delete file '{file_name}': {e}")
        else:
            st.sidebar.info("No files uploaded for this section.")
    except Exception as e:
        st.sidebar.error(f"Failed to retrieve files: {e}")

    # Sidebar: Breadcrumb display
    uploaded_sections = get_uploaded_sections(SECTION_KEYWORDS)
    if "uploaded_sections" not in st.session_state:
        st.session_state.uploaded_sections = set()

    if files:
        st.session_state.uploaded_sections.add(section)

    if st.session_state.uploaded_sections:
        breadcrumb_text = " > ".join(sorted(st.session_state.uploaded_sections))
        st.sidebar.info(f"📂 Sections with uploads: {breadcrumb_text}")
        
if __name__ == "__main__":
    main()