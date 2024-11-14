import numpy as np
import concurrent.futures
import os
from dotenv import load_dotenv
import structlog
from pydantic import BaseModel
from abc import ABC, abstractmethod
import re
import openai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import faiss
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain_openai import ChatOpenAI
from document_processor import SECTION_KEYWORDS

# Load environment variables
load_dotenv()

# Logger setup
def get_logger(cls: str):
    return structlog.get_logger().bind(cls=cls)

logger = get_logger(__name__)

# API Key retrieval
api_key = os.getenv("OPENAI_API_KEY")


class BasePromptTemplate(ABC, BaseModel):
    @abstractmethod
    def create_template(self, *args) -> PromptTemplate:
        pass


class QueryExpansionTemplate(BasePromptTemplate):
    prompt: str = """You are an AI language model assistant. Your task is to generate {to_expand_to_n}
    different versions of the given user question to retrieve relevant documents from a vector
    database. By generating multiple perspectives on the user question, your goal is to help
    the user overcome some of the limitations of the distance-based similarity search.
    Provide these alternative questions separated by '{separator}'.
    Original question: {question}"""

    def create_template(self, to_expand_to_n: int) -> PromptTemplate:
        return PromptTemplate(
            template=self.prompt,
            input_variables=["question"],
            partial_variables={
                "separator": self.separator,
                "to_expand_to_n": to_expand_to_n,
            },
        )

    @property
    def separator(self) -> str:
        return "#next-question#"


class SelfQueryTemplate(BasePromptTemplate):
    prompt: str = """You are an AI language model assistant. Your task is to extract information from a user question.
    The required information that needs to be extracted is the user or author id. 
    Your response should consist of only the extracted id (e.g. 1345256), nothing else.
    User question: {question}"""

    def create_template(self) -> PromptTemplate:
        return PromptTemplate(template=self.prompt, input_variables=["question"])


class RerankingTemplate(BasePromptTemplate):
    prompt: str = """You are an AI language model assistant. Your task is to rerank passages related to a query
    based on their relevance. 
    You should only return the summary of the most relevant passage.
    
    The following are passages related to this query: {question}.
    
    Passages: 
    {passages}
    
    Please provide only the summary of the most relevant passage.
    """

    def create_template(self, keep_top_k: int) -> PromptTemplate:
        return PromptTemplate(
            template=self.prompt,
            input_variables=["question", "passages"],
            partial_variables={"keep_top_k": keep_top_k},
        )

    @property
    def separator(self) -> str:
        return "\n#next-document#\n"


class GeneralChain:
    @staticmethod
    def get_chain(llm, template: PromptTemplate, output_key: str, verbose=True):
        return LLMChain(
            llm=llm, prompt=template, output_key=output_key, verbose=verbose
        )
        

# Chunking logic (as provided)
def _split_sentences(text):
    sentences = re.split(r'(?<=[.?!])\s+', text)
    return sentences

def _combine_sentences(sentences):
    combined_sentences = []
    for i in range(len(sentences)):
        combined_sentence = sentences[i]
        if i > 0:
            combined_sentence = sentences[i-1] + ' ' + combined_sentence
        if i < len(sentences) - 1:
            combined_sentence += ' ' + sentences[i+1]
        combined_sentences.append(combined_sentence)
    return combined_sentences

def create_faiss_index(embeddings):
    """
    Create a FAISS index from the given embeddings.
    
    Args:
    embeddings (numpy.array): The embeddings to index.
    
    Returns:
    faiss.Index: The created FAISS index.
    """
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index

def convert_to_vector(texts):

    # Try to generate embeddings for a list of texts using a pre-trained model and handle any exceptions.
    try:
        response = openai.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        embeddings = np.array([item.embedding for item in response.data])
        return embeddings
    except Exception as e:
        print("An error occurred:", e)
        return np.array([])

# def convert_to_vector(texts):
#     try:
#         response = openai.embeddings.create(
#             input=texts,
#             model="text-embedding-3-small"
#         )
#         embeddings = np.array([item.embedding for item in response.data])
#         return embeddings
#     except Exception as e:
#         print("An error occurred:", e)
#         return np.array([])

def _calculate_cosine_distances(embeddings):
    distances = []
    for i in range(len(embeddings) - 1):
        similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
        distance = 1 - similarity
        distances.append(distance)
    return distances


class RAGPipeline:
    def __init__(self, documents: list, api_key: str, k: int = 5, to_expand_to_n_queries: int = 3, keep_top_k: int = 1):
        """
        Initialize the RAG pipeline.

        Args:
        documents (list): List of documents.
        api_key (str): OpenAI API key.
        k (int): Number of top results to retrieve.
        to_expand_to_n_queries (int): Number of queries to expand to.
        keep_top_k (int): Number of top results to keep.
        """
        self.documents = documents
        self.api_key = api_key
        self.k = k
        self.to_expand_to_n_queries = to_expand_to_n_queries
        self.keep_top_k = keep_top_k
        self._embedder = OpenAIEmbeddings(api_key=api_key)
        self._query_expander = QueryExpansionTemplate()
        self._reranker = RerankingTemplate()
        # self.faiss_index = self._create_faiss_index(documents)

    def chunk_text(documents):
        single_sentences_list = _split_sentences(documents)
        combined_sentences = _combine_sentences(single_sentences_list)
        embeddings = convert_to_vector(combined_sentences)
        distances = _calculate_cosine_distances(embeddings)
        breakpoint_percentile_threshold = 80
        breakpoint_distance_threshold = np.percentile(distances, breakpoint_percentile_threshold)
        indices_above_thresh = [i for i, distance in enumerate(distances) if distance > breakpoint_distance_threshold]
        chunks = []
        start_index = 0
        for index in indices_above_thresh:
            chunk = ' '.join(single_sentences_list[start_index:index+1])
            chunks.append(chunk)
            start_index = index + 1
            if start_index < len(single_sentences_list):
                chunk = ' '.join(single_sentences_list[start_index:])
                chunks.append(chunk)
                return chunks

    def retrieve_top_k(self, query: str) -> list:
        """
        Retrieve the top-k relevant documents using the expanded queries.

        Args:
        query (str): The query to retrieve documents for.

        Returns:
        list: The top-k relevant documents.
        """
        # Generate expanded queries
        expanded_queries = self._query_expander.expand_query(query, self.to_expand_to_n_queries)

        # Concurrent search for each query
        hits = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            search_tasks = [
                executor.submit(self._search_single_query, expanded_query) for expanded_query in expanded_queries
            ]
            hits = [task.result() for task in concurrent.futures.as_completed(search_tasks)]

        # Flatten the results from the different queries
        hits = [item for sublist in hits for item in sublist]

        return hits

    def _search_single_query(self, query: str) -> list:
        """
        Search the FAISS index for a single query.

        Args:
        query (str): The query to search for.

        Returns:
        list: The search results.
        """
        query_vector = self._embedder.embed_query(query)
        D, I = self.faiss_index.search(query_vector, self.k)

        # D: distances, I: indices
        results = []
        for idx in I[0]:
            if idx != -1:
                doc = self.documents[idx]
                results.append({
                    "text": doc,
                    "source": "Unknown source",
                })

        return results

    def rerank(self, hits: list, query: str) -> str:
        """
        Rerank the retrieved documents and return the best answer with its source.

        Args:
        hits (list): The retrieved documents.

        Returns:
        str: The best answer and its source.
        """
        # Extract the 'text' field from each hit
        content_list = [hit['text'] for hit in hits]

        # Generate reranking based on the retrieved documents
        reranking_template = self._reranker.create_template(self.keep_top_k)
        prompt_template = reranking_template

        model = ChatOpenAI(
            model="gpt-4-1106-preview",
            api_key=self.api_key,
            temperature=0,
        )

        chain = GeneralChain().get_chain(
            llm=model, output_key="rerank", template=prompt_template
        )

        # Prepare passages for reranking
        passages = reranking_template.separator.join([item.strip() for item in content_list if item.strip()])
        response = chain.invoke({"question": query, "passages": passages})

        result = response["rerank"]
        reranked_passages = result.strip().split(reranking_template.separator)
        reranked_passages = [item.strip() for item in reranked_passages if item.strip()]

        # Return the best ranked passage and its source(s)
        if reranked_passages:
            best_answer = reranked_passages[0]
            best_answer_source = "Unknown source"  
            logger.info(f"Best answer selected: {best_answer}, Source: {best_answer_source}")
            return best_answer, best_answer_source
        else:
            return "", "No source found"

    def run_pipeline(self, query: str) -> dict:
        """
        Run the RAG pipeline for the given query.

        Args:
        query (str): The query to run the pipeline for.

        Returns:
        dict: The best answer and its source.
        """
        # Retrieve the top-k relevant documents using the expanded queries
        hits = self.retrieve_top_k(query)

        # Rerank the retrieved documents and return the best answer with its source
        best_answer, best_answer_source = self.rerank(hits)

        return {"answer": best_answer, "source": best_answer_source}

    def set_documents(self, documents: list):
        """
        Set the documents for the pipeline.

        Args:
        documents (list): The list of documents.
        """
        self.documents = documents
        self.faiss_index = self._create_faiss_index(documents)

    def set_query_expander(self, query_expander: QueryExpansionTemplate):
        """
        Set the query expander for the pipeline.

        Args:
        query_expander (QueryExpansionTemplate): The query expander.
        """
        self._query_expander = query_expander

    def set_reranker(self, reranker: RerankingTemplate):
        """
        Set the reranker for the pipeline.

        Args:
        reranker (RerankingTemplate): The reranker.
        """
        self._reranker = reranker
        
    def identify_section(self, question):
        """
        Identify section based on keywords in the question for targeted retrieval.
        Returns the matching section name or None.
        """
        for section, keywords in SECTION_KEYWORDS.items():
            if any(keyword.lower() in question.lower() for keyword in keywords):
                return section
        return None



# class RAGPipeline(BaseModel):
#     documents: Optional[List[Dict[str, str]]] = Field(default=None)  # Allow documents as dictionaries
    
#     def __init__(self, documents=None, **data):
#         super().__init__(documents=documents, **data)
#         self.query_expander = QueryExpansion()
#         self.reranker = Reranker()
#         self.self_query_processor = SelfQueryProcessor()
        
#         self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
#         self.faiss_index = None
        
#         if self.documents:
#             self.build_index(self.documents)
    
#     def build_index(self, documents: List[Dict[str, str]]):
#         # Extract text content and create embeddings
#         texts = [doc['text'] for doc in documents if 'text' in doc]
#         embeddings = [self.embedding_model.embed(text) for text in texts]
#         self.faiss_index = FAISS.from_embeddings(embeddings, texts)

#     def query(self, question: str, top_k: int = 5) -> List[str]:
#         if not self.faiss_index:
#             return []
        
#         question_embedding = self.embedding_model.embed(question)
#         relevant_docs = self.faiss_index.similarity_search_by_vector(question_embedding, k=top_k)
        
#         return relevant_docs

#     def identify_section(self, question):
#         """
#         Identify section based on keywords in the question for targeted retrieval.
#         Returns the matching section name or None.
#         """
#         for section, keywords in SECTION_KEYWORDS.items():
#             if any(keyword.lower() in question.lower() for keyword in keywords):
#                 return section
#         return None

#     def process_query(self, query: str, to_expand_to_n: int, keep_top_k: int) -> dict:
#         # Step 1: Expand the Query
#         expanded_queries = self.query_expander.generate_response(query, to_expand_to_n)
        
#         # Step 2: Self-query Processing (optional, if user ID extraction is needed)
#         user_id = self.self_query_processor.extract_user_id(query)

#         # Step 3: Retrieve relevant documents
#         relevant_docs = self.query(query, top_k=keep_top_k)

#         # Step 4: Rerank Passages
#         reranked_passages = self.reranker.rerank_passages(query, relevant_docs, keep_top_k)

#         # Return the expanded, reranked data
#         return {
#             "expanded_queries": expanded_queries,
#             "user_id": user_id,
#             "reranked_passages": reranked_passages,
#         }
