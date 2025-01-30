import google.generativeai as genai
import typing_extensions, json



class ExampleQueriesEntities(typing_extensions.TypedDict):
    example_queries: list[str]
    entity_types: list[str]
    

def generate_example_queries_entities(content:str):
    try:
        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

        result = model.generate_content(
            f"<content> {content} </content>\n\nExtract ten example questions(containing conceptual and direct questions) and eight entity types from the content provided",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema = ExampleQueriesEntities),
            request_options={"timeout": 600},
        )
        
        return json.loads(result.text)
        
     
    except Exception as e:
        print(e)
        
def is_supported_file_format(file_name):
    supported_formats = [".txt", ".pdf"]
    return any(file_name.endswith(ext) for ext in supported_formats)
    
