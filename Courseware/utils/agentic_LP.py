# agentic_LP.py

import tempfile
from docxtpl import DocxTemplate
from Courseware.utils.helper import process_logo_image

LP_TEMPLATE_DIR = "Courseware/input/Template/LP_TGS-Ref-No_Course-Title_v1.docx" 

def generate_lesson_plan(context: dict, name_of_organisation) -> str:
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