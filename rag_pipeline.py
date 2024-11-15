import os
import concurrent.futures
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from pydantic import BaseModel
import structlog
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain_openai import ChatOpenAI
from document_processor import DocumentProcessor

# Load environment variables
load_dotenv()

# Logger setup
def get_logger(cls: str):
    return structlog.get_logger().bind(cls=cls)

logger = get_logger(__name__)

# API Key retrieval
api_key = os.getenv("OPENAI_API_KEY")
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


# General Chain Class
class GeneralChain:
    @staticmethod
    def get_chain(llm, template: PromptTemplate, output_key: str, verbose=True):
        return LLMChain(
            llm=llm, prompt=template, output_key=output_key, verbose=verbose
        )


# Query Expansion Class
class QueryExpansion:
    @staticmethod
    def generate_response(query: str, to_expand_to_n: int, api_key: str) -> list[str]:
        query_expansion_template = QueryExpansionTemplate()
        prompt_template = query_expansion_template.create_template(to_expand_to_n)
        model = ChatOpenAI(
            model="gpt-4-1106-preview",
            api_key=api_key,
            temperature=0,
        )

        chain = GeneralChain().get_chain(
            llm=model, output_key="expanded_queries", template=prompt_template
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
    def generate_response(query: str, api_key: str) -> str:
        prompt = SelfQueryTemplate().create_template()
        model = ChatOpenAI(
            model="gpt-4-1106-preview",
            api_key=api_key,
            temperature=0,
        )

        chain = GeneralChain().get_chain(
            llm=model, output_key="metadata_filter_value", template=prompt
        )

        response = chain.invoke({"question": query})
        result = response["metadata_filter_value"]

        return result


# Reranker Class
class Reranker:
    @staticmethod
    def generate_response(
        query: str, passages: list[str], keep_top_k: int, api_key: str
    ) -> list[str]:
        reranking_template = RerankingTemplate()
        prompt_template = reranking_template.create_template(keep_top_k=keep_top_k)

        model = ChatOpenAI(
            model="gpt-4-1106-preview",
            api_key=api_key,
            temperature=0,
        )
        chain = GeneralChain().get_chain(
            llm=model, output_key="rerank", template=prompt_template
        )

        stripped_passages = [
            stripped_item for item in passages if (stripped_item := item.strip())
        ]
        passages = reranking_template.separator.join(stripped_passages)
        response = chain.invoke({"question": query, "passages": passages})

        result = response["rerank"]
        reranked_passages = result.strip().split(reranking_template.separator)
        stripped_passages = [
            stripped_item
            for item in reranked_passages
            if (stripped_item := item.strip())
        ]

        return stripped_passages


# RAG Pipeline Class
class RAGPipeline:
    def __init__(self, faiss_index, document_embeddings, documents, api_key, 
                 k=5, to_expand_to_n_queries=3, keep_top_k=1):
        self.faiss_index = faiss_index
        self.document_embeddings = document_embeddings
        self.documents = documents
        self.api_key = api_key
        self.k = k
        self.to_expand_to_n_queries = to_expand_to_n_queries
        self.keep_top_k = keep_top_k
        self._query_expander = QueryExpansion()
        self._metadata_extractor = SelfQuery()
        self._reranker = Reranker()
        self._embedder = OpenAIEmbeddings(api_key=api_key)
        # Initialize the executor for asynchronous task submission
        self._executor = concurrent.futures.ThreadPoolExecutor()

    def retrieve_top_k(self, query: str, k: int, to_expand_to_n_queries: int, api_key: str, include_metadata: bool) -> list:
        self.query = query
        
        # Generate expanded queries
        generated_queries = self._query_expander.generate_response(
            query=self.query,
            to_expand_to_n=to_expand_to_n_queries,
            api_key=api_key
        )
        
        # Process each expanded query
        search_tasks = []
        for query in generated_queries:
            # Ensure include_metadata is passed in the search task
            search_tasks.append(self._executor.submit(self._search_single_query, query, api_key, include_metadata))

        # Collect search results
        hits = [task.result() for task in concurrent.futures.as_completed(search_tasks)]
        return hits


    def _search_single_query(self, query: str, api_key: str) -> list:
        # Debugging: print the arguments
        print(f"Debug: _search_single_query called with query={query} and api_key={api_key}")
        
        query_vector = self._embedder.embed_query(query)  # Embed query here
        D, I = self.faiss_index.search(query_vector, self.k)
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
        content_list = [hit['text'] for hit in hits]
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

        passages = reranking_template.separator.join([item.strip() for item in content_list if item.strip()])
        response = chain.invoke({"question": query, "passages": passages})

        result = response["rerank"]
        reranked_passages = result.strip().split(reranking_template.separator)
        reranked_passages = [item.strip() for item in reranked_passages if item.strip()]

        if reranked_passages:
            best_answer = reranked_passages[0]
            best_answer_source = "Unknown source"
            logger.info(f"Best answer selected: {best_answer}, Source: {best_answer_source}")
            return best_answer, best_answer_source
        else:
            return "", "No source found"

    def run_pipeline(self, query: str, api_key: str, include_metadata: bool) -> dict:
        hits = self.retrieve_top_k(query, self.k, self.to_expand_to_n_queries, api_key=api_key, include_metadata=include_metadata)
        best_answer, best_answer_source = self.rerank(hits, query)
        return {"answer": best_answer, "source": best_answer_source}


    def identify_section(self, question):
        for section, keywords in process_document.section_keywords.items():
            if any(keyword in question.lower() for keyword in keywords):
                return section
        return "General"
