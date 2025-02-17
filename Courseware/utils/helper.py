import re
import json
import os
import pandas as pd

def parse_json_content(content):
    # Check if the content is wrapped in ``````
    json_pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
    match = json_pattern.search(content)
    
    if match:
        # If ```json ``` is present, extract the JSON content
        json_str = match.group(1)
    else:
        # If no ```json ```, assume the entire content is JSON
        json_str = content
    
    # Remove any leading/trailing whitespace
    json_str = json_str.strip()
    
    try:
        # Parse the JSON string
        parsed_json = json.loads(json_str)
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None

def save_uploaded_file(uploaded_file, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    file_path = os.path.join(save_dir, uploaded_file.name)
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def retrieve_excel_data(context: dict, sfw_dataset_dir: str) -> dict:
    # Load the Excel file
    excel_data = pd.ExcelFile(sfw_dataset_dir)
    
    # Load the specific sheet named 'TSC_K&A'
    df = excel_data.parse('TSC_K&A')
    
    tsc_code = context.get("TSC_Code")
    # Filter the DataFrame based on the TSC Code
    filtered_df = df[df['TSC Code'] == tsc_code]
    
    if not filtered_df.empty:
        row = filtered_df.iloc[0]
        
        context["TSC_Sector"] = str(row['Sector'])
        context["TSC_Sector_Abbr"] = str(tsc_code.split('-')[0])
        context["TSC_Category"] = str(row['Category'])
        context["Proficiency_Level"] = str(row['Proficiency Level'])
        context["Proficiency_Description"] = str(row['Proficiency Description'])

    # Return the retrieved data as a dictionary
    return context
