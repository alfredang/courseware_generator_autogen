import json
import sys
import re
import openpyxl
from openpyxl.styles import Font
from openpyxl.富文本 import RichText, TextRun
import os

def process_excel_template_with_json(json_path, excel_template_path, output_excel_path):
    # Load the JSON data
    with open(json_path, 'r') as file:
        json_data = json.load(file)

    # Preprocess JSON keys to make them valid Python variable names
    def preprocess_json_keys(json_data):
        new_data = {}
        for key, value in json_data.items():
            # Remove special characters and adjust keys
            new_key = re.sub(r'[^0-9a-zA-Z_]', '_', key)
            new_key = new_key.strip('_')
            # Recursively preprocess if value is a dict
            if isinstance(value, dict):
                value = preprocess_json_keys(value)
            new_data[new_key] = value
        return new_data

    context = preprocess_json_keys(json_data)

    # List of placeholders to process (same as original script for context)
    placeholders_to_process = ['Placeholder_1'] + [f'Topics_{i}' for i in range(6)] + ['AssessmentJustification','Sequencing']

    # Process specified placeholders to structure the context for Excel formatting
    for placeholder in placeholders_to_process:
        if placeholder in context:
            value = context[placeholder]
            if isinstance(value, list) or isinstance(value, str): # Process lists and strings
                context[placeholder] = process_placeholder(value) # Use the existing process_placeholder


    # CHECK THE CONTEXT BEFORE RENDERING to Excel
    print("Context being passed to Excel template processing:")
    print(json.dumps(context, indent=4))

    # Load the Excel template workbook
    try:
        workbook = openpyxl.load_workbook(excel_template_path)
    except FileNotFoundError:
        print(f"Error: Excel template file not found at {excel_template_path}")
        sys.exit(1)

    placeholder_regex = re.compile(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}')

    # Process each sheet in the workbook
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        print(f"Processing sheet: {sheet_name}")

        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str): # Process only string cell values that might contain placeholders
                    original_cell_value = cell.value
                    rich_text_runs = [] # List to hold TextRun objects for RichText
                    last_pos = 0 # Track position in the original string

                    for match in placeholder_regex.finditer(original_cell_value):
                        placeholder_name = match.group(1)
                        start_pos = match.start()
                        end_pos = match.end()

                        # Add any text before the placeholder as a plain TextRun
                        if start_pos > last_pos:
                            plain_text_segment = original_cell_value[last_pos:start_pos]
                            rich_text_runs.append(TextRun(plain_text_segment, Font(bold=False)))

                        if placeholder_name in context:
                            placeholder_content = context[placeholder_name] # This is now the structured data from process_placeholder

                            if isinstance(placeholder_content, list): # Expecting list of dicts from process_placeholder
                                for item in placeholder_content:
                                    if item['type'] == 'paragraph':
                                        rich_text_runs.append(TextRun(item['content'], Font(bold=False)))
                                        rich_text_runs.append(TextRun("\n")) # Add newline after paragraph
                                    elif item['type'] == 'bullets':
                                        for bullet_item in item['content']:
                                            rich_text_runs.append(TextRun("·   ", Font(bold=False))) # Bullet character
                                            rich_text_runs.append(TextRun(bullet_item, Font(bold=False)))
                                            rich_text_runs.append(TextRun("\n")) # Newline after each bullet
                                    elif item['type'] == 'bold_paragraph':
                                        rich_text_runs.append(TextRun(item['content'], Font(bold=True))) # Bold
                                        rich_text_runs.append(TextRun("\n")) # Newline after bold paragraph
                            elif isinstance(placeholder_content, str): # Fallback for simple string placeholders if process_placeholder not used correctly
                                rich_text_runs.append(TextRun(placeholder_content, Font(bold=False)))
                                rich_text_runs.append(TextRun("\n"))
                            else: # Handle unexpected data type
                                rich_text_runs.append(TextRun(f"Error: Unexpected data type for placeholder '{placeholder_name}'", Font(color="FF0000")))
                                rich_text_runs.append(TextRun("\n"))


                        else: # Placeholder not found in context
                            rich_text_runs.append(TextRun(f"{{{{{placeholder_name}}}}} (Not Found)", Font(color="0000FF"))) # Indicate missing placeholder in blue

                        last_pos = end_pos # Update last processed position

                    # Add any remaining text after the last placeholder
                    if last_pos < len(original_cell_value):
                        remaining_text = original_cell_value[last_pos:]
                        rich_text_runs.append(TextRun(remaining_text, Font(bold=False)))

                    if rich_text_runs: # Only set RichText if there's content
                        cell.value = RichText(rich_text_runs)
                    else: # If the cell was just a placeholder that resolved to nothing, you might want to clear it or leave it as is.
                        cell.value = "" # Or cell.value = None to clear the cell completely

    # Save the modified workbook
    try:
        workbook.save(output_excel_path)
        print(f"Updated Excel file saved to: {output_excel_path}")
    except Exception as e:
        print(f"Error saving Excel file: {e}")


def process_placeholder(value):
    import re
    items = []

    # Define the phrases to be bolded
    bold_phrases = ["Performance Gaps:", "Attributes Gained:", "Post-Training Benefits to Learners:"]

    # If value is a list, process each entry in the list
    if isinstance(value, list):
        for idx, entry in enumerate(value):
            lines = entry.split('\n')
            current_paragraph = []
            bullet_points = []

            for line in lines:
                line = line.strip()

                if not line:
                    # Empty line encountered; finalize current paragraph or bullets
                    if current_paragraph:
                        items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                        current_paragraph = []
                    if bullet_points:
                        items.append({'type': 'bullets', 'content': bullet_points})
                        bullet_points = []
                    # Do not add empty paragraph for spacing

                elif line.startswith('•'):
                    # Bullet point
                    if current_paragraph:
                        items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                        current_paragraph = []
                    bullet_points.append(line.lstrip('•').strip())

                elif re.match(r'^LU\d+:\s', line) or line in bold_phrases:
                    # LU title or specific bold phrases
                    if current_paragraph:
                        items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                        current_paragraph = []
                    if bullet_points:
                        items.append({'type': 'bullets', 'content': bullet_points})
                        bullet_points = []
                    # Add the line as a bold paragraph
                    items.append({'type': 'bold_paragraph', 'content': line})

                else:
                    # Regular line
                    if bullet_points:
                        items.append({'type': 'bullets', 'content': bullet_points})
                        bullet_points = []
                    current_paragraph.append(line)

            # Handle any remaining content in the entry
            if current_paragraph:
                items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                current_paragraph = []
            if bullet_points:
                items.append({'type': 'bullets', 'content': bullet_points})
                bullet_points = []

    else:
        # Handle single string value (e.g., Conclusion)
        lines = value.split('\n')
        current_paragraph = []
        bullet_points = []

        for line in lines:
            line = line.strip()

            if not line:
                # Empty line encountered; finalize current paragraph or bullets
                if current_paragraph:
                    items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                    current_paragraph = []
                if bullet_points:
                    items.append({'type': 'bullets', 'content': bullet_points})
                    bullet_points = []
                # Do not add empty paragraph for spacing

            elif line.startswith('•'):
                if current_paragraph:
                    items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                    current_paragraph = []
                bullet_points.append(line.lstrip('•').strip())

            elif line in bold_phrases:
                # Specific bold phrases
                if current_paragraph:
                    items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
                    current_paragraph = []
                if bullet_points:
                    items.append({'type': 'bullets', 'content': bullet_points})
                    bullet_points = []
                # Add the line as a bold paragraph
                items.append({'type': 'bold_paragraph', 'content': line})

            else:
                if bullet_points:
                    items.append({'type': 'bullets', 'content': bullet_points})
                    bullet_points = []
                current_paragraph.append(line)

        if current_paragraph:
            items.append({'type': 'paragraph', 'content': ' '.join(current_paragraph)})
        if bullet_points:
            items.append({'type': 'bullets', 'content': bullet_points})

    return items


# Example of how to use this function
if __name__ == "__main__":
    # Ensure correct number of arguments
    if len(sys.argv) != 4:
        print("Usage: python script.py <json_file> <excel_template> <new_excel>")
        sys.exit(1)

    # Parameters
    json_file = os.path.join('..', 'data', 'generated_mapping.json')
    excel_template_file = os.path.join('..', 'templates', 'CP_excel_template.xlsx')
    output_excel_file = os.path.join('..', 'output_docs', 'updated_CP.xlsx')

    # Call the function
    process_excel_template_with_json(json_file, excel_template_file, output_excel_file)
