# agentic_FG.py

import tempfile
from docxtpl import DocxTemplate
from Courseware.utils.helper import retrieve_excel_data, process_logo_image

FG_TEMPLATE_DIR = "Courseware/input/Template/FG_TGS-Ref-No_Course-Title_v1.docx"  
    
def generate_facilitators_guide(context: dict, name_of_organisation: str, sfw_dataset_dir=None) -> str:
    # Use the provided template directory or default
    if sfw_dataset_dir is None:
        sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"

    sfw_dataset_dir = "Courseware/input/dataset/Sfw_dataset-2022-03-30 copy.xlsx"
    context = retrieve_excel_data(context, sfw_dataset_dir)

    doc = DocxTemplate(FG_TEMPLATE_DIR)
    
    # Add the logo to the context
    context['company_logo'] = process_logo_image(doc, name_of_organisation)
    context['Name_of_Organisation'] = name_of_organisation

    doc.render(context, autoescape=True)
    # Use a temporary file to save the document
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        doc.save(tmp_file.name)
        output_path = tmp_file.name  # Get the path to the temporary file

    return output_path  # Return the path to the temporary file