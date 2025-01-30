import json
import logging
import os
import numpy as np
import streamlit as st
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, openai_complete_if_cache, gpt_4o_complete
from lightrag.utils import EmbeddingFunc
from filereader import extract_text_from_pdf


# Helper Function to Clean and Parse JSON
def clean_and_parse_json(raw_json):
    try:
        fixed_json = raw_json.replace("{{", "{").replace("}}", "}")
        return json.loads(fixed_json)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}. Raw data: {raw_json}")
        return None

# Asynchronous LLM Model Function
async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    raw_result = await openai_complete_if_cache(
        "solar-mini",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=st.secrets["UPSTAGE_API_KEY"],
        base_url="https://api.upstage.ai/v1/solar",
        **kwargs
    )

    if keyword_extraction:
        kw_prompt_json = clean_and_parse_json(raw_result)
        if not kw_prompt_json:
            return "Error: Unable to extract keywords."
        return json.dumps(kw_prompt_json)

    return raw_result


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

# Set up working directory for LightRAG
WORKING_DIR = "./document_repository"
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

# Initialize LightRAG with OpenAI model
rag = LightRAG(
    working_dir=WORKING_DIR,
    llm_model_func=gpt_4o_complete,
    embedding_func=EmbeddingFunc(
                embedding_dim=3072,
                max_token_size=8192,
                func=embedding_func
            )
)

st.title("Enhanced RAG with LightRAG")
st.write("Upload a document and ask questions based on structured knowledge retrieval.")

# File upload
uploaded_file = st.sidebar.file_uploader("Upload a file", type=["pdf", "txt"])

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type == "text/plain":
        text = uploaded_file.read().decode("utf-8")
    
    # Insert document into LightRAG
    rag.insert(text)
    st.success("Document processed and indexed!")

    # Query input
    query = st.text_input("Ask a question about the document:")
    if query:
        search_mode = st.sidebar.selectbox("Select retrieval mode", ["local", "global", "hybrid", "mix"])
        response = rag.query(query, param=QueryParam(mode=search_mode))
        st.write("### Answer:")
        st.write(response)
