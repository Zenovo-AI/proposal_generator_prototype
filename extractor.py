import google.generativeai as genai
import textwrap
import json
import openai

openai.api_key = st.secrets["OPENAI"]["OPENAI_API_KEY"]

model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

class EntityRelationshipExtractor:
    def __init__(self, model_name="models/gemini-1.5-flash", api_key=None):
        """
        Initialize Gemini model or equivalent API for entity and relationship extraction.
        """
        self.model_name = model_name
        self.api_key = api_key

    def extract_entities_and_relationships(self, text):
        """
        Extract entities and relationships from the provided text using Gemini API.
        Args:
            text (str): The text to process.
        Returns:
            dict: A dictionary containing entities and relationships in JSON format.
        """
        # Construct the prompt for the generative model
        prompt = textwrap.dedent(
            f"""
            Please return JSON describing the people, places, things, and relationships from this text using the following schema:

            {{
                "people": list[PERSON],
                "places": list[PLACE],
                "things": list[THING],
                "relationships": list[RELATIONSHIP]
            }}

            PERSON = {{"name": str, "description": str, "start_place_name": str, "end_place_name": str}}
            PLACE = {{"name": str, "description": str}}
            THING = {{"name": str, "description": str, "start_place_name": str, "end_place_name": str}}
            RELATIONSHIP = {{"person_1_name": str, "person_2_name": str, "relationship": str}}

            All fields are required. Important: Only return a single piece of valid JSON text.

            Here is the text:
            {text}
            """
        )

        # Generate response from the model
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )

        # Extract and parse the generated text from the response object
        if hasattr(response, "text"):
            response_text = response.text  # Use `response.text` as per documentation
            print(f"Response object: {response}")

            try:
                return json.loads(response_text)  # Convert the JSON string to a Python dictionary
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response: {e}")
        else:
            raise ValueError("The response object does not contain 'generated_text'.")
        
    def generate_example_queries(self, text, num_queries=10):
        """
        Generate example queries based on the entities and relationships in the text.
        Args:
            text (str): The text to process.
            num_queries (int): Number of queries to generate.
        Returns:
            List[str]: A list of example queries.
        """
        # Construct the prompt for generating queries
        prompt = textwrap.dedent(
            f"""
            Based on the following text, generate {num_queries} example queries for interacting with its content. 
            Focus on the entities and relationships present in the text.

            Text:
            {text}
            """
        )

        # Generate response from the model
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "text/plain"},
        )

        # Extract the generated text and split into queries
        if hasattr(response, "text"):
            print(f"GENERATED QUERIES: {response}")
            return response.text.strip().split("\n")  # Assuming newline-separated queries
        else:
            raise ValueError("The response object does not contain 'generated_text'.")

