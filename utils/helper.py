import os
import re
import json

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