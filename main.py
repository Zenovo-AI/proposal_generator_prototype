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
        
        user_input = st.text_input("Ask a question about hospital policies:")
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




# import streamlit as st
# from document_processor import DocumentProcessor
# from rag_pipeline import RAGPipeline
# from chat_bot import ChatBot
# import cryptography

# # Display the cryptography version
# st.write(f"Cryptography version: {cryptography.__version__}")

# # Initialize session state
# if "section_files" not in st.session_state:
#     st.session_state.section_files = {}
# if "section_embeddings" not in st.session_state:
#     st.session_state.section_embeddings = {}  # Maps section to embeddings and vector databases
# if 'rag_pipeline' not in st.session_state:
#     st.session_state.rag_pipeline = None
# if 'chat_bot' not in st.session_state:
#     st.session_state.chat_bot = None
# if 'chat_history' not in st.session_state:
#     st.session_state.chat_history = []

# # Instantiate the DocumentProcessor
# process_document = DocumentProcessor()

# def main():
#     st.title("Hospital Policy Chat Bot")
    
#     # Section to upload and process documents
#     st.header("Upload and Manage Documents")
#     section = st.sidebar.selectbox("Select a document section:", options=list(process_document.SECTION_KEYWORDS.keys()))
    
#     # Display files already uploaded in the selected section
#     if section in st.session_state.section_files:
#         st.write(f"Files in '{section}' section:")
#         for file_name in st.session_state.section_files[section]:
#             st.write(file_name)
#     else:
#         st.write(f"No files uploaded yet in '{section}' section.")
    
#     # File uploader for the section
#     uploaded_file = st.sidebar.file_uploader(f"Upload a file to '{section}' section", type=["pdf", "txt"])
#     if uploaded_file:
#         # Save the uploaded file to the session state for the selected section
#         if section not in st.session_state.section_files:
#             st.session_state.section_files[section] = []
#         st.session_state.section_files[section].append(uploaded_file.name)
        
#         # Save file using DocumentProcessor
#         process_document.save_uploaded_file(uploaded_file, section)
#         st.success(f"File '{uploaded_file.name}' saved to '{section}' section.")
    
#     # Optional URL input
#     web_url = st.sidebar.text_input("Optionally, enter a URL of a policy webpage")
    
#     # Process documents and initialize RAG pipeline
#     if st.button("Process Documents"):
#         if section in st.session_state.section_files or web_url:
#             with st.spinner("Processing documents..."):
#                 # Process files and URL
#                 vectordb, documents = process_document.process_and_chunk_text(
#                     st.session_state.section_files.get(section, []),
#                     web_url,
#                     section
#                 )
#                 # Initialize the RAG pipeline and chatbot
#                 st.session_state.rag_pipeline = RAGPipeline(vectordb, documents)
#                 st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
#             st.success("Documents processed successfully!")
#         else:
#             st.warning("Please upload a document or enter a URL.")

#     # Chat interface
#     if st.session_state.rag_pipeline:
#         st.header("Chat with the Bot")
#         user_input = st.text_input("Ask a question about hospital policies:")
#         if st.button("Send") and user_input.strip():
#             response = st.session_state.chat_bot.get_response(user_input)
#             st.session_state.chat_history.append(("You", user_input))
#             st.session_state.chat_history.append(("Bot", response))
#             # Display last 10 messages
#             st.session_state.chat_history = st.session_state.chat_history[-10:]
        
#         # Display chat history
#         st.write("### Chat History")
#         for role, message in st.session_state.chat_history:
#             st.write(f"**{role}:** {message}")
#     else:
#         st.info("Please process documents before interacting with the bot.")

# if __name__ == "__main__":
#     main()




# import streamlit as st
# from document_processor import DocumentProcessor
# from rag_pipeline import RAGPipeline
# from chat_bot import ChatBot
# import cryptography


# # # Print the version of the cryptography package
# st.write(f"Cryptography version: {cryptography.__version__}")

# # Initialize session state for storing section files


# process_document = DocumentProcessor()

# def save_uploaded_file(uploaded_file, section):
#     """
#     Save an uploaded file in the session state for a specific section.
#     """
#     if section not in st.session_state.section_files:
#         st.session_state.section_files[section] = []
    
#     # Check if file is already in the section
#     file_names = [file['name'] for file in st.session_state.section_files[section]]
#     if uploaded_file.name not in file_names:
#         st.session_state.section_files[section].append({
#             "name": uploaded_file.name,
#             "content": uploaded_file.getvalue(),
#             "type": uploaded_file.type
#         })

# def list_files_in_section(section):
#     """
#     List all files in the session state for a section.
#     """
#     return [file["name"] for file in st.session_state.section_files.get(section, [])]

# def main():
#     st.title("Hospital Policy Chat Bot")

#     # Section to upload and process documents
#     st.sidebar.header("Upload Policy Documents")
#     section = st.sidebar.selectbox("Choose document section:", options=list(process_document.SECTION_KEYWORDS.keys()))

#     # Show existing files for the selected section
#     st.sidebar.subheader("Existing Files in Section")
#     existing_files = list_files_in_section(section)
#     if existing_files:
#         st.sidebar.write("\n".join(existing_files))
#     else:
#         st.sidebar.write("No files uploaded for this section.")

#     uploaded_files = st.sidebar.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
#     web_url = st.sidebar.text_input("Enter URL of policy webpage")

#     if st.sidebar.button("Process Documents"):
#         if uploaded_files or web_url:
#             # Save uploaded files to the selected section
#             for uploaded_file in uploaded_files:
#                 save_uploaded_file(uploaded_file, section)

#             with st.spinner("Processing documents..."):
#                 # Retrieve files from session state for processing
#                 files_content = [file["content"] for file in st.session_state.section_files.get(section, [])]
#                 vectordb, documents = process_document.process_and_chunk_text(files_content, web_url, section)
#                 st.session_state.rag_pipeline = RAGPipeline(vectordb, documents)
#                 st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
#                 st.success("Documents processed successfully!")
#         else:
#             st.warning("Please upload a document or enter a URL.")

#     # Chatbot interface section after documents are processed
#     if st.session_state.rag_pipeline:
#         st.header("Chat Interface")

#         user_input = st.text_area("What is your question?")
#         if st.button("Send") and user_input.strip():
#             response = st.session_state.chat_bot.get_response(user_input)
#             st.write(f"**Bot:** {response}")
#         else:
#             st.warning("Please process documents before starting the chat.")

# if __name__ == "__main__":
#     main()



# import streamlit as st
# from document_processor import DocumentProcessor
# from rag_pipeline import RAGPipeline
# from chat_bot import ChatBot
# import uuid
# import cryptography


# # Print the version of the cryptography package
# st.write(f"Cryptography version: {cryptography.__version__}")
# print(f"Cryptography version: {cryptography.__version__}")  # This line is to also ensure it prints to the console

# if "section_files" not in st.session_state:
#     st.session_state.section_files = {}

# # Initialize session state
# if 'rag_pipeline' not in st.session_state:
#     st.session_state.rag_pipeline = None
# if 'chat_bot' not in st.session_state:
#     st.session_state.chat_bot = None
# if 'chat_history' not in st.session_state:
#     st.session_state.chat_history = []
    
# process_document = DocumentProcessor()

# def main():
#     st.title("Hospital Policy Chat Bot")
    
#     # Section to upload and process documents
#     st.header("Upload Policy Documents")
#     section = st.selectbox("Choose document section:", options=list(process_document.SECTION_KEYWORDS.keys()))
#     uploaded_files = st.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
#     web_url = st.text_input("Enter URL of policy webpage")

#     if st.button("Process Documents"):
#         # Process documents and initialize pipeline if files or URL provided
#         if uploaded_files or web_url:
#             with st.spinner("Processing documents..."):
#                 vectordb, documents = process_document.process_and_chunk_text(uploaded_files, web_url, section)

#                 # Initialize the RAGPipeline with the documents
#                 st.session_state.rag_pipeline = RAGPipeline(vectordb, documents)
#                 st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
#             st.success("Documents processed successfully!")
#         else:
#             st.warning("Please upload a document or enter a URL.")

#     # Chatbot interface section after documents are processed
#     if st.session_state.rag_pipeline:
#         st.header("Chat Interface")
        
#         # Query input field appears only after documents are processed
#         user_input = st.text_input("Ask a question about hospital policies:")
        
#         if st.button("Send") and user_input.strip():  # Added input validation
#             # Get the response from the chatbot
#             response = st.session_state.chat_bot.get_response(user_input)
#             # Append the conversation to the chat history
#             st.session_state.chat_history.append(("You", user_input))
#             st.session_state.chat_history.append(("Bot", response))
            
#             # Limit chat history display to 10 messages
#             st.session_state.chat_history = st.session_state.chat_history[-10:]
        
#         # Display the chat history
#         for role, message in st.session_state.chat_history:
#             st.text_area(role, value=message, height=100, key=f"response_text_{uuid.uuid4()}", disabled=True)
#     else:
#         # Show message prompting for document processing if not done yet
#         st.warning("Please process documents before starting the chat.")

# if __name__ == "__main__":
#     main()

# import os
# import streamlit as st
# from document_processor import DocumentProcessor
# from rag_pipeline import RAGPipeline
# from chat_bot import ChatBot
# import uuid
# import cryptography

# # Print the version of the cryptography package
# st.write(f"Cryptography version: {cryptography.__version__}")
# print(f"Cryptography version: {cryptography.__version__}")  # This line is to also ensure it prints to the console

# # Ensure `uploaded_files` directory exists
# if not os.path.exists('uploaded_files'):
#     os.makedirs('uploaded_files')

# # Initialize session state
# if 'rag_pipeline' not in st.session_state:
#     st.session_state.rag_pipeline = None
# if 'chat_bot' not in st.session_state:
#     st.session_state.chat_bot = None
# if 'chat_history' not in st.session_state:
#     st.session_state.chat_history = []

# process_document = DocumentProcessor()

# def main():
#     st.title("Hospital Policy Chat Bot")
    
#     # Section to upload and process documents
#     st.header("Upload Policy Documents")
#     section = st.sidebar.selectbox("Choose document section:", options=list(process_document.SECTION_KEYWORDS.keys()))
#     uploaded_files = st.sidebar.file_uploader("Upload PDF or TXT documents", type=["pdf", "txt"], accept_multiple_files=True)
#     web_url = st.sidebar.text_input("Enter URL of policy webpage")

#     if st.button("Process Documents"):
#         # Process documents and initialize pipeline if files or URL provided
#         if uploaded_files or web_url:
#             with st.spinner("Processing documents..."):
#                 vectordb, documents = process_document.process_and_chunk_text(uploaded_files, web_url, section)

#                 # Initialize the RAGPipeline with the documents
#                 st.session_state.rag_pipeline = RAGPipeline(vectordb, documents)
#                 st.session_state.chat_bot = ChatBot(st.session_state.rag_pipeline)
#             st.success("Documents processed successfully!")
#         else:
#             st.warning("Please upload a document or enter a URL.")

#     # Chatbot interface section after documents are processed
#     if st.session_state.rag_pipeline:
#         st.header("Chat Interface")
        
#         # Query input field appears only after documents are processed
#         user_input = st.text_area("What is :")
        
#         if st.button("Send") and user_input.strip():  # Added input validation
#             # Get the response from the chatbot
#             response = st.session_state.chat_bot.get_response(user_input)
#             # Append the conversation to the chat history
#             st.session_state.chat_history.append(("You", user_input))
#             st.session_state.chat_history.append(("Bot", response))
            
#             # Limit chat history display to 10 messages
#             st.session_state.chat_history = st.session_state.chat_history[-10:]

#         # Dropdown to select the chat history section to view
#         history_section = st.selectbox("Select chat history section:", ["All", "You", "Bot"])
        
#         # Filter chat history based on selected section
#         if history_section == "All":
#             for role, message in st.session_state.chat_history:
#                 st.write(f"**{role}:** {message}")
#         else:
#             for role, message in st.session_state.chat_history:
#                 if role == history_section:
#                     st.write(f"**{role}:** {message}")
#     else:
#         # Show message prompting for document processing if not done yet
#         st.warning("Please process documents before starting the chat.")

# if __name__ == "__main__":
#     main()
