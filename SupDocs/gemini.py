# gemini_processor.py

import os
import json
from google.generativeai import Gemini

# Set your Gemini API key (environment variable is recommended)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

gemini = Gemini(GEMINI_API_KEY)

def extract_entities(document_content, custom_instructions):
    """
    Extracts named entities from the document content using Gemini,
    customized with user-provided instructions.
    """

    prompt = f"""
    Extract named entities from the following document content, 
    following these instructions: {custom_instructions}

    Document Content:
    ```
    {document_content}
    ```

    Return the extracted entities in a structured JSON format.  
    For each entity, include its type, value, and any relevant context 
    from the document.  If no entities are found, return an empty JSON object.
    """

    try:
        response = gemini.generate_text(
            model="gemini-pro",  # Or the appropriate Gemini model
            prompt=prompt,
            temperature=0.0,  # Adjust for creativity vs. accuracy
            max_output_tokens=2048, # Adjust as needed
        )
        
        # Attempt to parse the JSON response. Handle potential errors gracefully.
        try:
            extracted_entities = json.loads(response.result)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from Gemini response: {response.result}")
            extracted_entities = {} # Return empty if JSON is invalid.

        return extracted_entities

    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return {}  # Return empty dictionary in case of error



def process_document(file_path, custom_instructions):
    """Reads the document content and calls the extraction function."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:  # Handle encoding
            document_content = f.read()
    except Exception as e:  # Handle file reading errors
        print(f"Error reading file: {e}")
        return {}

    return extract_entities(document_content, custom_instructions)