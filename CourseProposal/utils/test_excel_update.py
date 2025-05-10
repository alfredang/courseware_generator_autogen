import json
import os
from utils.excel_replace_xml import process_excel_update, preserve_excel_metadata, cleanup_old_files
from utils.excel_conversion_pipeline import map_new_key_names_excel
from utils.helpers import load_json_file

def test_course_outline_formatting():
    """
    Test the updated course outline formatting in the Excel generation process.
    """
    # Define paths
    json_data_path = "json_output/generated_mapping.json"
    excel_template_path = "templates/course_proposal_form_01apr2025_template.xlsx"
    output_excel_path_modified = "output_docs/CP_template_updated_cells_output.xlsx"
    output_excel_path_preserved = "output_docs/CP_template_metadata_preserved.xlsx"
    ensemble_output_path = "json_output/ensemble_output.json"
    excel_data_path = "json_output/excel_data.json"
    
    # Load necessary data
    ensemble_output = load_json_file(ensemble_output_path)
    generated_mapping = load_json_file(json_data_path)
    
    # Process the course outline formatting
    map_new_key_names_excel(json_data_path, generated_mapping, json_data_path, excel_data_path, ensemble_output)
    
    # Clean up old files
    cleanup_old_files(output_excel_path_modified, output_excel_path_preserved)
    
    # Process Excel update
    process_excel_update(json_data_path, excel_template_path, output_excel_path_modified, ensemble_output_path)
    
    # Preserve metadata
    preserve_excel_metadata(excel_template_path, output_excel_path_modified, output_excel_path_preserved)
    
    print("Excel generation complete!")
    
    # Optionally, load and print the generated mapping to verify the course outline
    updated_mapping = load_json_file(json_data_path)
    course_outline = updated_mapping.get("#Course_Outline", "Not found")
    print("\nGenerated Course Outline:")
    print(course_outline)

if __name__ == "__main__":
    test_course_outline_formatting() 