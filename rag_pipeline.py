import concurrent.futures
import streamlit as st
from abc import ABC, abstractmethod
from pydantic import BaseModel
import structlog
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from langchain_groq import ChatGroq



# Logger setup
def get_logger(cls: str):
    return structlog.get_logger().bind(cls=cls)

logger = get_logger(__name__)


            
# session_manager = SessionManager()
# api_key = session_manager.get_api_key()
GROQ_API_KEY = st.secrets["GROQ"]["GROQ_API_KEY"]
model_name = "Llama-3.1-70b-versatile"

llm = ChatGroq(groq_api_key=GROQ_API_KEY, model_name=model_name)


# Base class for prompt templates
class BasePromptTemplate(ABC, BaseModel):
    @abstractmethod
    def create_template(self, *args) -> PromptTemplate:
        pass


# Query Expansion Template
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
        self.tokenizer = AutoTokenizer.from_pretrained("cross-encoder/stsb-distilroberta-base")
        self.model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/stsb-distilroberta-base")

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
        print(hits_with_scores)

        # Identify the most relevant passage
        if hits_with_scores:
            best_answer = hits_with_scores[0][0][0].page_content  # Access the text attribute of the best hit
            return best_answer
        else:
            return None

# RAG Pipeline Class
class RAGPipeline:
    def __init__(self, vectordb, documents,
                 k=5, to_expand_to_n_queries=3, keep_top_k=1):
        self.faiss_index = vectordb
        print(self.faiss_index)
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.documents = documents
        self.llm = llm
        self.k = k
        self.to_expand_to_n_queries = to_expand_to_n_queries
        self.keep_top_k = keep_top_k
        self._query_expander = QueryExpansion()
        self._metadata_extractor = SelfQuery()
        self.reranker = Reranker()
        self._embedder = HuggingFaceEmbeddings()
        # Initialize the executor for asynchronous task submission
        self._executor = concurrent.futures.ThreadPoolExecutor()

    
    def retrieve_top_k(self, query: str, k: int, to_expand_to_n_queries: int):
        # Perform query expansion
        expanded_queries = self._query_expander.generate_response(query, to_expand_to_n_queries)
        print(f"Expanded Queries: {expanded_queries}")
        
        # Retrieve documents using FAISS index for each expanded query
        results = []
        for expanded_query in expanded_queries:
            result = self.faiss_index.similarity_search_with_score(expanded_query, k=k)
            results.extend(result)
        
        print(f"Debug: _search_single_query called with expanded queries={expanded_queries}")
        return results

    def paraphrase_answer(self, answer: str) -> str:
        # Create a prompt template
        template = PromptTemplate(
            input_variables=["text"],
            template="Please condense and rephrase the following text to answer the question clearly and concisely. NO PREAMBLE and NO NEW QUESTION, JUST PARAPHRASE THE ANSWER: {text}",
        )
        
        # Create a prompt dictionary with the correct format
        prompt = {"text": answer}
        
        # Get the LLM response
        chain = GeneralChain().get_chain(llm=self.llm, template=template, output_key="paraphrased_answer")
        response = chain.invoke(prompt)
        
        # Extract the paraphrased answer
        paraphrased_answer = response["paraphrased_answer"]
        
        return paraphrased_answer

    def run_pipeline(self, query: str) -> str:
        # Retrieve the top-k relevant passages
        hits = self.retrieve_top_k(query, self.k, self.to_expand_to_n_queries)
        
        # Get the best answer from reranking
        best_answer = self.reranker.rerank(query, hits)
        print(f"best answer: {best_answer}")
        
        # Paraphrase the best answer using LLM
        if best_answer:
            paraphrased_answer = self.paraphrase_answer(best_answer)
            
            # Format the paraphrased answer
            formatted_answer = paraphrased_answer.strip()
            
            return formatted_answer
        else:
            return "No relevant passage found."
