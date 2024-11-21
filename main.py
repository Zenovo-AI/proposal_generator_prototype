import streamlit as st
from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot

process_document = DocumentProcessor()

# Initialize session state variables
if 'rag_pipeline' not in st.session_state:
    st.session_state.rag_pipeline = None
if 'chat_bot' not in st.session_state:
    st.session_state.chat_bot = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'section_documents' not in st.session_state:
    st.session_state.section_documents = {}  # To store uploaded files by section
if 'section_embeddings' not in st.session_state:
    st.session_state.section_embeddings = {}  # To store embeddings by section

def main():
    st.title("Proposal Generator")

    # Sidebar for selecting a section and uploading files
    section = st.sidebar.selectbox(
        "Select a document section:",
        options=list(process_document.SECTION_KEYWORDS)
    )

    # Display uploaded documents for the selected section
    st.sidebar.write("Uploaded Documents:")
    if section in st.session_state.section_documents:
        for doc_name in st.session_state.section_documents[section]:
            st.sidebar.write(f"- {doc_name}")
    else:
        st.sidebar.write("No documents uploaded yet.")

    # File uploader for the selected section
    uploaded_files = st.sidebar.file_uploader(
        f"Upload a file to '{section}' section",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        # Process and store uploaded files
        with st.spinner("Processing documents..."):
            file_names = [file.name for file in uploaded_files]
            vectordb, documents = process_document.process_and_chunk_text(
                uploaded_files, section=section
            )
            st.session_state.section_embeddings[section] = (vectordb, documents)

            # Save uploaded files to session state
            if section not in st.session_state.section_documents:
                st.session_state.section_documents[section] = []
            st.session_state.section_documents[section].extend(file_names)
            
            st.success("Documents processed and embeddings saved.")

    # Chatbot logic
    if section in st.session_state.section_embeddings:
        st.header("Chat with the Bot")
        vectordb, documents = st.session_state.section_embeddings[section]
        st.session_state.chat_bot = ChatBot(RAGPipeline(vectordb, documents))

        user_input = st.text_input("Ask your question:")
        if st.button("Send") and user_input.strip():
            response = st.session_state.chat_bot.get_response(user_input)
            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", response))
            st.write("### Chat History")
            for role, message in st.session_state.chat_history[-10:]:
                st.write(f"**{role}:** {message}")
    else:
        st.info("Process documents before chatting with the bot.")

if __name__ == "__main__":
    main()
