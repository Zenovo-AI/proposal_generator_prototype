import streamlit as st
from document_processor import process_documents
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot
import os
# Initialize session state
if 'rag_pipeline' not in st.session_state:
    st.session_state.rag_pipeline = None
if 'chat_bot' not in st.session_state:
    st.session_state.chat_bot = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
def main():
    st.title("Hospital Policy Chat Bot")
    # Document processing section
    st.header("Document Processing")

    # List existing files
    existing_files = os.listdir('uploaded_files') if os.path.exists('uploaded_files') else []
    st.write("Existing files:", existing_files)

    documents = []  # Initialize documents as an empty list

    # Option to use existing files
    use_existing = st.checkbox("Use existing files")
    if use_existing:
        selected_files = st.multiselect("Select files to process", existing_files)
        if st.button("Process Selected Files"):
            if selected_files:
                with st.spinner("Processing documents..."):
                    documents = process_documents([open(os.path.join('uploaded_files', f), 'rb') for f in selected_files], None)
                    if documents:
                        print("Processed Documents (existing files):", documents)
                        st.session_state.rag_pipeline = RAGPipeline(documents)
                        st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
                    else:
                        st.error("Failed to process documents")
                    st.success("Documents processed successfully!")
            else:
                st.warning("No files selected for processing.")
    else:
        uploaded_files = st.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
        web_url = st.text_input("Enter URL of policy webpage")

        if st.button("Process Documents"):
            if uploaded_files or web_url:
                with st.spinner("Processing documents..."):
                    documents = process_documents(uploaded_files, web_url)
                    if documents:
                        print("Processed Documents (uploaded):", documents)
                        st.session_state.rag_pipeline = RAGPipeline(documents)
                        st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
                    else:
                        st.error("Failed to process documents")
                    st.success("Documents processed successfully!")
            else:
                st.warning("Please upload documents or provide a URL.")

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