import numpy as np
import concurrent.futures
from llm_helper import llm
from abc import ABC, abstractmethod
from pydantic import BaseModel
import structlog
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from document_processor import DocumentProcessor

# Logger setup
def get_logger(cls: str):
    return structlog.get_logger().bind(cls=cls)

logger = get_logger(__name__)

process_document = DocumentProcessor()

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
    based on their relevance. 
    You should return only the most relevant passage and its source.

    The following are passages related to this query: {question}.
    
    Passages: 
    {passages}
    
    Please provide only the text of the most relevant passage and its source in the format:
    "<passage_text>"
    "Source: <source>"
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


# Reranker Class
class Reranker:
    def __init__(self):
        self.reranking_template = RerankingTemplate()

    def generate_response(
        self, query: str, passages: list[str], keep_top_k: int
    ) -> list[str]:
        prompt_template = self.reranking_template.create_template(keep_top_k=keep_top_k)
        chain = GeneralChain().get_chain(
            llm=llm, output_key="rerank", template=prompt_template
        )

        stripped_passages = [
            stripped_item for item in passages if (stripped_item := item.strip())
        ]
        passages = self.reranking_template.separator.join(stripped_passages)
        response = chain.invoke({"question": query, "passages": passages})

        result = response["rerank"]
        reranked_passages = result.strip().split(self.reranking_template.separator)
        stripped_passages = [
            stripped_item
            for item in reranked_passages
            if (stripped_item := item.strip())
        ]

        return stripped_passages
    
    def create_template(self, keep_top_k: int) -> PromptTemplate:
        return self.reranking_template.create_template(keep_top_k)
    
    @property
    def separator(self) -> str:
        return self.reranking_template.separator


# RAG Pipeline Class
class RAGPipeline:
    def __init__(self, vectordb, documents,  embedding_model = "sentence-transformers/all-MiniLM-L6-v2",
                 k=5, to_expand_to_n_queries=3, keep_top_k=1):
        self.faiss_index = vectordb
        self.embedding_model = HuggingFaceEmbeddings(model_name=embedding_model)
        self.documents = documents
        self.llm = llm
        self.k = k
        self.to_expand_to_n_queries = to_expand_to_n_queries
        self.keep_top_k = keep_top_k
        self._query_expander = QueryExpansion()
        self._metadata_extractor = SelfQuery()
        self._reranker = Reranker()
        self._embedder = HuggingFaceEmbeddings()
        # Initialize the executor for asynchronous task submission
        self._executor = concurrent.futures.ThreadPoolExecutor()

    def retrieve_top_k(self, query: str, k: int, to_expand_to_n_queries: int):
        self.query = query
        
        # Generate expanded queries
        generated_queries = self._query_expander.generate_response(
            query=self.query,
            to_expand_to_n=to_expand_to_n_queries
        )
        
        # Process each expanded query
        search_tasks = []
        for query in generated_queries:
            # Ensure include_metadata is passed in the search task
            search_tasks.append(self._executor.submit(self._search_single_query, query))

        # Collect search results
        hits = [task.result() for task in concurrent.futures.as_completed(search_tasks)]
        return hits


    def _search_single_query(self, query: str):
        # Debugging: print the arguments
        print(f"Debug: _search_single_query called with query={query}")
        
        # Retrieve documents using FAISS index
        retriever = self.faiss_index.as_retriever()
        results = retriever.invoke(query)
        print(results)
        
        # Format results
        formatted_results = [
            {"text": result.page_content, "source": result.metadata.get("source")}
            for result in results
        ]
        
        return formatted_results


    def rerank(self, hits: list, query: str):
        print(hits)
        # Flatten the list of hits
        flat_hits = [item for sublist in hits for item in sublist]

        # Extract content and sources from hits
        content_list = [
            {"text": hit["text"], "source": hit.get("source")}
            for hit in flat_hits if "text" in hit and hit["text"]
        ]

        # Use a default separator if not defined in the reranker template
        reranking_template = self._reranker.create_template(self.keep_top_k)
        separator = "\n\n"  # Default separator
        if hasattr(reranking_template, "separator"):
            separator = reranking_template.separator

        # Combine passages into a single string for processing
        passages = separator.join([item["text"].strip() for item in content_list if item["text"].strip()])

        # Create and run the chain
        chain = GeneralChain().get_chain(
            llm=self.llm, output_key="rerank", template=reranking_template
        )
        response = chain.invoke({"question": query, "passages": passages})

        # Process the chain response to get reranked passages
        result = response["rerank"]
        reranked_passages = result.strip().split(separator)
        reranked_passages = [item.strip() for item in reranked_passages if item.strip()]
        print(reranked_passages)

        # Identify the most relevant passage and its source
        if reranked_passages:
            best_answer_text = reranked_passages[0]
            best_answer_source = next(
                (item["source"] for item in content_list if item["text"].strip() == best_answer_text),
                "."
            )
            return best_answer_text, best_answer_source
        else:
            return None, None  # Return None if no valid passages are found

    
    
    def run_pipeline(self, query: str) -> dict:
        # Retrieve the top-k relevant passages
        hits = self.retrieve_top_k(query, self.k, self.to_expand_to_n_queries)
        
        # Get the best answer and its source from reranking
        best_answer, best_answer_source = self.rerank(hits, query)
        print(f"best answer: {best_answer}")
        print(f"best source: {best_answer_source}")
        
        # Prepare a clean result for display or further use
        if best_answer and best_answer_source:
            return {best_answer, best_answer_source}
        else:
            return {"answer": "No relevant passage found.", "source": "No source found."}


    def identify_section(self, question):
        for section, keywords in process_document.section_keywords.items():
            if any(keyword in question.lower() for keyword in keywords):
                return section
        return "General"
