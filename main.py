import os
import streamlit as st
from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot
import uuid
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
    
process_document = DocumentProcessor()

def main():
    st.title("Hospital Policy Chat Bot")
    
    # Section to upload and process documents
    st.header("Upload Policy Documents")
    section = st.selectbox("Choose document section:", options=list(process_document.SECTION_KEYWORDS.keys()))
    uploaded_files = st.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
    web_url = st.text_input("Enter URL of policy webpage")

    if st.button("Process Documents"):
        # Process documents and initialize pipeline if files or URL provided
        if uploaded_files or web_url:
            with st.spinner("Processing documents..."):
                vectordb, documents = process_document.process_and_chunk_text(uploaded_files, web_url, section)

                # Initialize the RAGPipeline with the documents
                st.session_state.rag_pipeline = RAGPipeline(vectordb, documents)
                st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
            st.success("Documents processed successfully!")
        else:
            st.warning("Please upload a document or enter a URL.")

    # Chatbot interface section after documents are processed
    if st.session_state.rag_pipeline:
        st.header("Chat Interface")
        
        # Query input field appears only after documents are processed
        user_input = st.text_input("Ask a question about hospital policies:")
        
        if st.button("Send") and user_input.strip():  # Added input validation
            # Get the response from the chatbot
            response = st.session_state.chat_bot.get_response(user_input)
            # Append the conversation to the chat history
            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("Bot", response))
            
            # Limit chat history display to 10 messages
            st.session_state.chat_history = st.session_state.chat_history[-10:]
        
        # Display the chat history
        for role, message in st.session_state.chat_history:
            st.text_area(role, value=message, height=100, key=f"response_text_{uuid.uuid4()}", disabled=True)
    else:
        # Show message prompting for document processing if not done yet
        st.warning("Please process documents before starting the chat.")

if __name__ == "__main__":
    main()