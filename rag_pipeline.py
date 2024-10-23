from pydantic import BaseModel
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import nltk
from nltk.tokenize import sent_tokenize
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Download the punkt tokenizer for sentence splitting
nltk.download('punkt', quiet=True)

class DocumentConfig(BaseModel):
    model_name: str
    content: str

    class Config:
        protected_namespaces = ()

class RAGPipeline(BaseModel):
    documents: list[DocumentConfig]

    class Config:
        protected_namespaces = ()

    def __init__(self, documents):
        self.documents = documents
        self.text_splitter = self._create_text_splitter()
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = self._create_vector_store()

    def _create_text_splitter(self):
        return RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def _split_into_sentences(self, text):
        return sent_tokenize(text)

    def _create_vector_store(self):
        texts = []
        metadatas = []
        for doc in self.documents:
            sentences = self._split_into_sentences(doc.content)
            chunks = self.text_splitter.create_documents(sentences)
            texts.extend([chunk.page_content for chunk in chunks])
            metadatas.extend([{"source": doc.model_name} for _ in chunks])

        return FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)

    def query(self, question, k=3):
        results = self.vector_store.similarity_search_with_score(question, k=k)
        return [(doc.page_content, doc.metadata["source"], score) for doc, score in results]