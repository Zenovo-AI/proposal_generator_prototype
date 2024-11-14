import os
import streamlit as st
import document_processor
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot
import uuid

# Create directories if they don't exist
if not os.path.exists('uploaded_files'):
    os.makedirs('uploaded_files')

# Initialize session state variables
from document_processor import process_documents
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot
import cryptography

# Print the version of the cryptography package
st.write(f"Cryptography version: {cryptography.__version__}")
print(f"Cryptography version: {cryptography.__version__}")  # This line is to also ensure it prints to the console

# Ensure `uploaded_files` directory exists
if not os.path.exists('uploaded_files'):
    os.makedirs('uploaded_files')

# Initialize session state
if 'rag_pipeline' not in st.session_state:
    st.session_state.rag_pipeline = None
if 'chat_bot' not in st.session_state:
    st.session_state.chat_bot = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def main():
    st.title("Hospital Policy Chat Bot")
    
    # Section to upload and process documents
    st.header("Upload Policy Documents")
    section = st.selectbox("Choose document section:", options=list(document_processor.SECTION_KEYWORDS.keys()))
    uploaded_files = st.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
    web_url = st.text_input("Enter URL of policy webpage")

    if st.button("Process Documents"):
        # Process documents and initialize pipeline if files or URL provided
        if uploaded_files or web_url:
            with st.spinner("Processing documents..."):
                documents = document_processor.process_documents(uploaded_files, web_url, section)
                # Initialize the RAGPipeline with the documents
                st.session_state.rag_pipeline = RAGPipeline(faiss_index=None, query=None, documents=documents)
                st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
            st.success("Documents processed successfully!")
        else:
            st.warning("Please upload a document or enter a URL.")

    # Chatbot interface section after documents are processed
    if st.session_state.rag_pipeline:
        st.header("Chat Interface")
        
        # Query input field appears only after documents are processed
        user_input = st.text_input("Ask a question about hospital policies:")
        
        if st.button("Send") and user_input:
            # Get the response from the chatbot
            response = st.session_state.chat_bot.get_response(user_input)
            # Append the conversation to the chat history
            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", response))

        # Display the chat history
        for role, message in st.session_state.chat_history:
            st.text_area(role, value=message, height=100, key=f"response_text_{uuid.uuid4()}", disabled=True)
    else:
        # Show message prompting for document processing if not done yet
        st.warning("Please process documents before starting the chat.")

if __name__ == "__main__":
    main()

def process_single_document(file_path):
    # Process a single document given its file path
    documents = process_documents([open(file_path, 'rb')], None)
    if documents:
        print("Processed Documents (single file):", documents)
        st.session_state.rag_pipeline = RAGPipeline(documents)
        st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
    else:
        st.error("Failed to process document")
    st.success("Document processed successfully!")

def main():
    st.title("Hospital Policy Chat Bot")

    # Document processing section
    st.header("Document Processing")
    existing_files = os.listdir('uploaded_files') if os.path.exists('uploaded_files') else []
    st.write("Existing files:", existing_files)
    documents = []

    if len(existing_files) == 1:
        # Automatically process the single file
        with st.spinner("Processing single document automatically..."):
            file_path = os.path.join('uploaded_files', existing_files[0])
            process_single_document(file_path)

    else:
        # User can choose to use existing documents or upload new ones
        use_existing = st.checkbox("Use existing files")
        if use_existing:
            selected_files = st.multiselect("Select files to process", existing_files)
            if selected_files:
                with st.spinner("Processing documents..."):
                    for selected_file in selected_files:
                        st.write(f"Processing file: {selected_file}")
                        file_path = os.path.join('uploaded_files', selected_file)
                        try:
                            process_single_document(file_path)
                        except Exception as e:
                            st.error(f"Error processing document: {selected_file}, Error: {e}")
                st.success("Documents processed successfully!")
            else:
                st.warning("No files selected for processing.")
        else:
            uploaded_files = st.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
            web_url = st.text_input("Enter URL of policy webpage")

            # Debugging: Check if files are being uploaded
            if uploaded_files:
                st.write(f"Uploaded files: {[file.name for file in uploaded_files]}")

                # Automatically process uploaded files
                with st.spinner("Processing uploaded documents..."):
                    try:
                        documents = process_documents(uploaded_files, web_url)
                        if documents:
                            print(f"Processed Documents (uploaded):", documents)
                            st.session_state.rag_pipeline = RAGPipeline(documents)
                            st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
                            st.success("Documents processed successfully!")
                        else:
                            st.error("Failed to process documents")
                    except Exception as e:
                        st.error(f"Error processing documents: {e}")

    # Chat interface
    st.header("Chat Interface")
    if st.session_state.chat_bot:
        user_input = st.text_input("Ask a question about hospital policies:")
        if st.button("Send"):
            response = st.session_state.chat_bot.get_response(user_input)
            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", response))

        # Display chat history
        for role, message in st.session_state.chat_history:
            if role == "You":
                st.text_area("You:", value=message, height=50, disabled=True)
            else:
                st.text_area("Bot:", value=message, height=100, disabled=True)
    else:
        st.warning("Please process documents before starting the chat.")

if __name__ == "__main__":
    main()

