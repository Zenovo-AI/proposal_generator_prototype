import requests
import streamlit as st

response = requests.post(
    "https://api.upstage.ai/v1/solar",
    headers={"Authorization": f"Bearer {st.secrets['UPSTAGE_API_KEY']}"},
    json={"texts": ["""Using larger embeddings, for example storing them in a vector store for retrieval, 
                    generally costs more and consumes more compute, memory and storage than using smaller embeddings.
                    Both of our new embedding models were trained with a techniqueA that allows developers to 
                    trade-off performance and cost of using embeddings. Specifically, developers can shorten 
                    embeddings (i.e. remove some numbers from the end of the sequence) without the embedding losing 
                    its concept-representing properties by passing in the dimensions API parameter. For example, on 
                    the MTEB benchmark, a text-embedding-3-large embedding can be shortened to a size of 256 while 
                    still outperforming an unshortened text-embedding-ada-002 embedding with a size of 1536."""]}  # Adjust payload if needed
)

print(response.status_code)
print(response.json())  # Check the response data
