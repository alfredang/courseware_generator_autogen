import pandas as pd
import os
from PIL import Image
from docx.shared import Inches
from docxtpl import InlineImage

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

def process_logo_image(doc, name_of_organisation, max_width_inch=7, max_height_inch=2.5):
    """
    Processes an organization's logo image for insertion into a Word document.

    Args:
        doc (DocxTemplate): The document where the image will be placed.
        name_of_organisation (str): The organization's name (used for logo file naming).
        max_width_inch (float): Maximum width allowed in inches.
        max_height_inch (float): Maximum height allowed in inches.

    Returns:
        InlineImage: The resized logo image for use in the document.
    """
    logo_filename = name_of_organisation.lower().replace(" ", "_") + ".jpg"
    logo_path = f"Courseware/utils/logo/{logo_filename}"

    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo file not found for organisation: {name_of_organisation}")

    # Open the logo image
    image = Image.open(logo_path)
    width_px, height_px = image.size

    # Get DPI and calculate dimensions in inches
    dpi = image.info.get('dpi', (96, 96))  # Default to 96 DPI if not specified
    width_inch = width_px / dpi[0]
    height_inch = height_px / dpi[1]

    # Scale dimensions if they exceed the maximum
    width_ratio = max_width_inch / width_inch if width_inch > max_width_inch else 1
    height_ratio = max_height_inch / height_inch if height_inch > max_height_inch else 1
    scaling_factor = min(width_ratio, height_ratio)

    # Apply scaling
    width_docx = Inches(width_inch * scaling_factor)
    height_docx = Inches(height_inch * scaling_factor)

    # Create and return the InlineImage
    return InlineImage(doc, logo_path, width=width_docx, height=height_docx)