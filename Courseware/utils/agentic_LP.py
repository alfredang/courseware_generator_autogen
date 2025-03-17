# agentic_LP.py

import tempfile
from docxtpl import DocxTemplate
from Courseware.utils.helper import process_logo_image

LP_TEMPLATE_DIR = "Courseware/input/Template/LP_TGS-Ref-No_Course-Title_v1.docx" 

def generate_lesson_plan(context: dict, name_of_organisation: str) -> str:
    """
    Generates a Lesson Plan (LP) document by filling in a template with provided course data.

    This function uses a DOCX template and populates it with the given `context` dictionary.
    It also processes and inserts the organization's logo into the document before rendering it.

    Args:
        context (dict): 
            A dictionary containing course-related details that will be used to populate the template.
        name_of_organisation (str): 
            The name of the organization, used to fetch and insert the corresponding logo.

    Returns:
        str: 
            The file path of the generated Lesson Plan document.

    Raises:
        FileNotFoundError: 
            If the template file or the organization's logo file is missing.
        KeyError: 
            If required keys are missing from the `context` dictionary.
        IOError: 
            If there are issues with reading/writing the document.
    """
    
    doc = DocxTemplate(LP_TEMPLATE_DIR)

    # Add the logo to the context
    context['company_logo'] = process_logo_image(doc, name_of_organisation)
    context['Name_of_Organisation'] = name_of_organisation

    doc.render(context, autoescape=True)
    
    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file
