import streamlit as st
from abc import ABC, abstractmethod
from pydantic import BaseModel
import structlog
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from langchain_openai import ChatOpenAI
from utils import create_empty_vectordb



# Logger setup
def get_logger(cls: str):
    return structlog.get_logger().bind(cls=cls)

logger = get_logger(__name__)


openai_apikey = st.secrets["OPENAI"]["OPENAI_API_KEY"]

llm = ChatOpenAI(
    model="gpt-4",
    openai_api_key=openai_apikey
    
)


# Base class for prompt templates
class BasePromptTemplate(ABC, BaseModel):
    @abstractmethod
    def create_template(self, *args) -> PromptTemplate:
        pass


# Query Expansion Template
class QueryExpansionTemplate(BasePromptTemplate):
    prompt: str = """You are an AI assistant helping to retrieve documents from a vector database. Generate {to_expand_to_n} variations of the given query to improve retrieval accuracy. Include:
    1. Queries that rephrase the original while keeping the intent.
    2. Domain-specific synonyms or related terms.
    3. Variations that include specific entities, contexts, or key phrases.
    Provide these queries separated by '{separator}'.
    Original query: {question}"""


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


# Self Query Template
class SelfQueryTemplate(BasePromptTemplate):
    prompt: str = """You are an AI language model assistant. Your task is to extract information from a user question.
    The required information to be extracted includes:
    Intent: The user's goal or purpose
    Entities: Specific objects, people, or locations mentioned
    Context: Relevant background information
    Keywords: Important words or phrases
    Your response should consist of these extracted details in the following format:
    Intent: {intent}
    Entities: {entities}
    Context: {context}
    Keywords: {keywords}
    User question: {question}"""

    def create_template(self) -> PromptTemplate:
        return PromptTemplate(template=self.prompt, input_variables=["question"])


# Reranking Template
class RerankingTemplate(BasePromptTemplate):
    prompt: str = """You are an AI language model assistant. Your task is to rerank passages related to a query
    based on their relevance and paraphrase the passages that it is very readable. 
    You should return only the most relevant passage.

    The following are passages related to this query: {question}.
    
    Passages: 
    {passages}
    
    Please provide only the text of the most relevant passage and its source in the format:
    "<passage_text>"
    """

    def create_template(self, keep_top_k: int) -> PromptTemplate:
        return PromptTemplate(
            template=self.prompt,
            input_variables=["question", "passages"],
            partial_variables={"keep_top_k": keep_top_k},
        )

    @property
    def separator(self) :
        return "\n#next-document#\n"


# General Chain Class
class GeneralChain:
    @staticmethod
    def get_chain(llm, template: PromptTemplate, output_key, verbose=True):
        return LLMChain(
            llm=llm, prompt=template, output_key=output_key, verbose=verbose
        )


# Query Expansion Class
class QueryExpansion:
    @staticmethod
    def generate_response(query: str, to_expand_to_n: int):
        query_expansion_template = QueryExpansionTemplate()
        prompt_template = query_expansion_template.create_template(to_expand_to_n)

        chain = GeneralChain().get_chain(
            llm=llm, output_key="expanded_queries", template=prompt_template
        )

        response = chain.invoke({"question": query})
        result = response["expanded_queries"]

        queries = result.strip().split(query_expansion_template.separator)
        stripped_queries = [
            stripped_item for item in queries if (stripped_item := item.strip())
        ]
        print(stripped_queries)

        return stripped_queries




# Self Query Class
class SelfQuery:
    @staticmethod
    def generate_response(query: str):
        prompt = SelfQueryTemplate().create_template()

        chain = GeneralChain().get_chain(
            llm=llm, output_key="metadata_filter_value", template=prompt
        )

        response = chain.invoke({"question": query})
        result = response["metadata_filter_value"]

        return result


class Reranker:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query: str, hits: list):
        # Prepare inputs for the model
        inputs = []
        for hit in hits:
            document, score = hit  # Unpack the tuple
            inputs.append(self.tokenizer.encode_plus(
                query,
                document.page_content,  # Access the text attribute of the Document object
                add_special_tokens=True,
                max_length=512,
                return_attention_mask=True,
                return_tensors="pt",
            ))

        # Get scores from the model
        scores = []
        with torch.no_grad():
            for input in inputs:
                outputs = self.model(**input)
                score = torch.softmax(outputs.logits, dim=1)[0, 0]  # Access the single score
                scores.append(score.item())

        # Combine hits with scores and sort
        hits_with_scores = list(zip(hits, scores))  # Use the original hit tuples
        hits_with_scores.sort(key=lambda x: x[1], reverse=True)

        # Identify the most relevant passage
        if hits_with_scores:
            best_answer = hits_with_scores[0][0][0].page_content  # Access the text attribute of the best hit
            return best_answer
        else:
            return None

# RAG Pipeline Class
class RAGPipeline:
    def __init__(self, vectordb, documents, k=5, to_expand_to_n_queries=3, keep_top_k=1):
        if vectordb is None or not hasattr(vectordb, "similarity_search_with_score"):
            print("No valid FAISS vector store provided. Initializing with placeholder.")
            vectordb = create_empty_vectordb()
        
        self.faiss_index = vectordb
        self.documents = documents
        self.k = k
        self.to_expand_to_n_queries = to_expand_to_n_queries
        self.keep_top_k = keep_top_k
        self._query_expander = QueryExpansion()
        self._metadata_extractor = SelfQuery()
        self.reranker = Reranker()
        self.llm = llm


        # Validate the faiss_index
        if self.faiss_index is None or not hasattr(self.faiss_index, "similarity_search_with_score"):
            raise ValueError("The provided vector database is invalid or does not support `similarity_search_with_score`.")

    def retrieve_top_k(self, query: str) -> list:
        """Retrieve top-k relevant documents from the vector database."""
        if not hasattr(self.faiss_index, "similarity_search_with_score"):
            raise ValueError("The vector database does not implement `similarity_search_with_score`.")

        # Expand the query
        expanded_queries = self._query_expander.generate_response(query, self.to_expand_to_n_queries)

        # Retrieve results for each expanded query
        results = []
        for expanded_query in expanded_queries:
            if hasattr(self.faiss_index, "similarity_search_with_score"):
                results.extend(self.faiss_index.similarity_search_with_score(expanded_query, k=self.k))
            else:
                print(f"Warning: The vector database doesn't support similarity search for query `{expanded_query}`.")

        return results

    def paraphrase_answer(self, answer: str) -> str:
        """Paraphrase the answer using the LLM."""
        template = PromptTemplate(
            input_variables=["text"],
            template="Please reformat the following response to ensure it is clear, structured, and professional. Use headings, bullet points, and a logical layout to organize the information effectively. Remove any unnecessary details, such as irrelevant introductory information like 'Vienna International Centre Address: P. O. Box 1200, A-1400 Vienna, Austria Website: www.ctbto.org' or footer references like 'Page 1 of 6.' Retain all critical details, ensure grammatical correctness, and make the content easy to read: {text}",
        )
        prompt = {"text": answer}
        chain = GeneralChain().get_chain(llm=self.llm, template=template, output_key="paraphrased_answer")
        response = chain.invoke(prompt)
        return response.get("paraphrased_answer", answer)

    def run_pipeline(self, query: str) -> str:
        """Run the RAG pipeline to get the final response."""
        # Retrieve relevant passages
        hits = self.retrieve_top_k(query)

        if not hits:
            return "No relevant passages found."

        # Rerank the hits
        best_answer = self.reranker.rerank(query, hits)

        if not best_answer:
            return "Unable to find a relevant answer."

        # Paraphrase the best answer
        return self.paraphrase_answer(best_answer)


