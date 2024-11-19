import streamlit as st
from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline
from chat_bot import ChatBot


process_document = DocumentProcessor()

if 'rag_pipeline' not in st.session_state:
    st.session_state.rag_pipeline = None
if 'chat_bot' not in st.session_state:
    st.session_state.chat_bot = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []


def main():
    st.title("Hospital Policy Chat Bot")
    
    section = st.sidebar.selectbox(
        "Select a document section:",
        options=list(process_document.SECTION_KEYWORDS)
    )

    uploaded_files = st.sidebar.file_uploader(
        f"Upload a file to '{section}' section",
        type=["pdf", "txt"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        with st.spinner("Processing documents..."):
            vectordb, documents = process_document.process_and_chunk_text(
                uploaded_files, section=section
            )
            st.session_state.section_embeddings[section] = (vectordb, documents)
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
