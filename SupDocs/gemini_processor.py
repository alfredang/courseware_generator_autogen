import google.generativeai as genai
import json
import re
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
import pandas as pd

# Configure Gemini API
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")  # Make sure to set this environment variable
genai.configure(api_key=GOOGLE_API_KEY)

# Configure Google Sheets API (replace with your credentials and sheet ID)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'path/to/your/credentials.json' # Replace with your service account credentials json file
SHEET_ID = 'your_google_sheet_id'  # Replace with your Google Sheet ID
SHEET_NAME = 'Sheet1'  # Replace with your sheet name if different

def configure_google_sheets():
    """Configures and returns a gspread client."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.Client(auth=creds)
    return client

def load_documents(document_paths):
    """Loads documents from given file paths.

    Args:
        document_paths: A list of file paths to the documents.

    Returns:
        A list of strings, where each string is the content of a document.
    """
    documents = []
    for path in document_paths:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                documents.append(file.read())
        except UnicodeDecodeError:
            # Handle files with different encoding, e.g., images read as bytes
            with open(path, 'rb') as file:
                # You might want to process these files differently,
                # e.g., using OCR for images
                documents.append(file.read())
        except Exception as e:
            print(f"Error reading file {path}: {e}")
    return documents

def extract_entities_with_gemini(document_content):
    """Extracts entities from a document using the Gemini API.

    Args:
        document_content: The content of the document as a string.

    Returns:
        A dictionary containing the extracted entities.
    """
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    You are an expert data analyst that is able to understand context of documents and extract information from the provided document.
    Extract the following entities from the document below:
    - Name: (Name of the person the document belongs to)
    - Date: (Date of the document, in YYYY-MM-DD format)
    - Company Name: (Name of the company)
    - Company UEN: (Company's UEN, if present. If not, state "Missing")

    Document:
    {document_content}
    """

    response = model.generate_content(prompt)

    # Use regular expressions to find the entities in the response text
    extracted_entities = {}
    extracted_entities["Name"] = re.search(r"Name:\s*(.*)", response.text).group(1) if re.search(r"Name:\s*(.*)", response.text) else "Not found"
    extracted_entities["Date"] = re.search(r"Date:\s*(.*)", response.text).group(1) if re.search(r"Date:\s*(.*)", response.text) else "Not found"
    extracted_entities["Company Name"] = re.search(r"Company Name:\s*(.*)", response.text).group(1) if re.search(r"Company Name:\s*(.*)", response.text) else "Not found"
    extracted_entities["Company UEN"] = re.search(r"Company UEN:\s*(.*)", response.text).group(1) if re.search(r"Company UEN:\s*(.*)", response.text) else "Missing"

    return extracted_entities

def validate_date(date_str):
    """Validates if the date string is in YYYY-MM-DD format.

    Args:
        date_str: The date string to validate.

    Returns:
        The date string if valid, otherwise "Invalid date format".
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        return "Invalid date format"

def store_extracted_data(extracted_data, output_filename="extracted_data.json"):
    """Stores the extracted data to a JSON file.

    Args:
        extracted_data: A list of dictionaries, where each dictionary contains
                        the extracted entities for a document.
        output_filename: The name of the output JSON file.
    """
    with open(output_filename, 'w') as f:
        json.dump(extracted_data, f, indent=4)

def extract_data_from_sheet(client, sheet_id, sheet_name):
    """Extracts relevant data from a specified Google Sheet.

    Args:
        client: The gspread client.
        sheet_id: The ID of the Google Sheet.
        sheet_name: The name of the sheet within the spreadsheet.

    Returns:
        A list of dictionaries, where each dictionary represents a row in the sheet.
    """
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    data = sheet.get_all_records()
    return data

def store_sheet_data(sheet_data, output_filename="sheet_data.json"):
    """Stores the Google Sheet data in a JSON file.

    Args:
        sheet_data: A list of dictionaries representing the sheet data.
        output_filename: The name of the output JSON file.
    """
    with open(output_filename, 'w') as f:
        json.dump(sheet_data, f, indent=4)

def compare_data(extracted_data, sheet_data):
    """Compares the extracted data with the Google Sheet data.

    Args:
        extracted_data: A list of dictionaries with extracted data.
        sheet_data: A list of dictionaries from the Google Sheet.

    Returns:
        A list of dictionaries, where each dictionary contains the comparison
        results for a single document.
    """
    comparison_results = []

    for extracted_doc in extracted_data:
        extracted_name = extracted_doc["Name"]
        best_match = {"match_score": 0, "sheet_entry": None}

        for sheet_entry in sheet_data:
            sheet_name = sheet_entry.get("Trainee Name", "")  # Adjust key as needed
            match_score = calculate_match_score(extracted_name, sheet_name)

            if match_score > best_match["match_score"]:
                best_match["match_score"] = match_score
                best_match["sheet_entry"] = sheet_entry

        comparison_result = {
            "document_data": extracted_doc,
            "best_match_from_sheet": best_match["sheet_entry"],
            "match_scores": {}
        }

        if best_match["sheet_entry"]:
            for key in ["Name", "Company Name", "Company UEN"]:
                comparison_result["match_scores"][key] = calculate_match_score(
                    extracted_doc[key], best_match["sheet_entry"].get(key, "")
                )

        comparison_results.append(comparison_result)

    return comparison_results

def calculate_match_score(str1, str2):
    """Calculates a simple match score between two strings (case-insensitive).

    Args:
        str1: The first string.
        str2: The second string.

    Returns:
        A match score between 0 and 100.
    """
    str1 = str1.lower()
    str2 = str2.lower()

    if str1 == str2:
        return 100
    elif str1 in str2 or str2 in str1:
        return 75  # Partial match
    else:
        return 0

# Example usage (you'll integrate this with Streamlit):
def process_documents(document_paths):
    """Loads, processes, and compares documents.

    Args:
        document_paths: A list of file paths to the documents.

    Returns:
        A tuple containing:
        - extracted_data: List of dictionaries with extracted entities.
        - sheet_data: List of dictionaries from the Google Sheet.
        - comparison_results: List of dictionaries with comparison results.
    """

    documents = load_documents(document_paths)

    extracted_data = []
    for doc in documents:
        if isinstance(doc, bytes):
            # Handle binary data (e.g., images) - you might need OCR here
            print("Binary data detected. OCR or other processing needed.")
            extracted_data.append({"Error": "Binary data, cannot extract text"})
            continue

        entities = extract_entities_with_gemini(doc)
        entities["Date"] = validate_date(entities["Date"])
        extracted_data.append(entities)

    store_extracted_data(extracted_data)

    # Google Sheets data extraction
    client = configure_google_sheets()
    sheet_data = extract_data_from_sheet(client, SHEET_ID, SHEET_NAME)
    store_sheet_data(sheet_data)

    # Data comparison
    comparison_results = compare_data(extracted_data, sheet_data)

    return extracted_data, sheet_data, comparison_results