import streamlit as st
from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot
import cryptography


# Display the cryptography version
st.write(f"Cryptography version: {cryptography.__version__}")

# Initialize session state
if "section_embeddings" not in st.session_state:
    st.session_state.section_embeddings = {}  # Maps section to embeddings and vector databases
if 'chat_bot' not in st.session_state:
    st.session_state.chat_bot = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Instantiate the DocumentProcessor
process_document = DocumentProcessor()

def main():
    st.title("Hospital Policy Chat Bot")
    
    # Section to upload and manage documents
    st.header("Upload and Manage Documents")
    section = st.sidebar.selectbox("Select a document section:", options=list(process_document.SECTION_KEYWORDS))
    
    # Display files already uploaded in the selected section
    if section in st.session_state.section_embeddings:
        st.write(f"Files processed in '{section}' section.")
    else:
        st.write(f"No documents processed yet in '{section}' section.")
    
    # File uploader for the section
    uploaded_files = st.sidebar.file_uploader(f"Upload a file to '{section}' section", type=["pdf", "txt"], accept_multiple_files=True)
    if uploaded_files:
        # Process the uploaded files immediately
        with st.spinner("Processing documents..."):
            vectordb, documents = process_document.process_and_chunk_text(uploaded_files, section=section)
            st.session_state.section_embeddings[section] = (vectordb, documents)
            st.success("Documents processed and embeddings saved.")

    # Optional URL input
    web_url = st.sidebar.text_input("Optionally, enter a URL of a policy webpage")
    
    
    # Process URL if provided
    if web_url:
        with st.spinner("Processing webpage..."):
            vectordb, documents = process_document.process_and_chunk_text([], web_url=web_url, section=section)
            st.session_state.section_embeddings[section] = (vectordb, documents)
            st.success("Webpage processed and embeddings saved.")
    
    # Chat interface
    if section in st.session_state.section_embeddings:
        st.header("Chat with the Bot")
        # Initialize chatbot for the selected section
        vectordb, documents = st.session_state.section_embeddings[section]
        st.session_state.chat_bot = ChatBot(RAGPipeline(vectordb, documents))
        
        user_input = st.text_input("Please feel free to ask your question:")
        if st.button("Send") and user_input.strip():
            response = st.session_state.chat_bot.get_response(user_input)
            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", response))
            # Display last 10 messages
            st.session_state.chat_history = st.session_state.chat_history[-10:]
        
        # Display chat history
        st.write("### Chat History")
        for role, message in st.session_state.chat_history:
            st.write(f"**{role}:** {message}")
    else:
        st.info("Please process documents for this section before interacting with the bot.")

if __name__ == "__main__":
    main()
