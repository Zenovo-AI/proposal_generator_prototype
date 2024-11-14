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
