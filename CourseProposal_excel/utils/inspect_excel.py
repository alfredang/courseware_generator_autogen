import os
import zipfile
import tempfile
import shutil
from lxml import etree as ET

def get_relationship_mapping(rels_path):
    ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
    tree = ET.parse(rels_path)
    root = tree.getroot()
    rels = {}
    for rel in root.findall('r:Relationship', ns):
        rId = rel.attrib.get('Id')
        target = rel.attrib.get('Target')  # e.g., "worksheets/sheet1.xml"
        # Prepend "xl/" if needed
        rels[rId] = os.path.join('xl', target) if not target.startswith('/') else target[1:]
    return rels

def get_sheet_mapping(workbook_xml_path, rels_map):
    """
    Returns a mapping from sheet name to its full XML file path (relative to the extracted directory)
    """
    ns = {
        'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    }
    tree = ET.parse(workbook_xml_path)
    root = tree.getroot()
    mapping = {}
    for sheet in root.xpath('.//main:sheets/main:sheet', namespaces=ns):
        name = sheet.get('name')
        rId = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        if rId in rels_map:
            mapping[name] = rels_map[rId]
    return mapping

def extract_xml_files(xlsx_path, output_folder, sheets_to_extract):
    """
    Unzips the given .xlsx file, and saves out key XML parts (workbook.xml, workbook.xml.rels,
    and the sheet XML files for each sheet in sheets_to_extract) to text files in output_folder.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        # Unzip the xlsx to a temporary folder.
        with zipfile.ZipFile(xlsx_path, 'r') as zin:
            zin.extractall(temp_dir)
        print(f"Extracted workbook to temporary directory: {temp_dir}")

        # Ensure the output folder exists.
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # List of common files to extract.
        common_files = [
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels"
        ]
        for file in common_files:
            src_path = os.path.join(temp_dir, file)
            if os.path.exists(src_path):
                with open(src_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Save with a modified file name (replace '/' with '_' for clarity)
                out_filename = file.replace('/', '_') + ".txt"
                out_path = os.path.join(output_folder, out_filename)
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Saved {file} to {out_path}")

        # Build the sheet mapping.
        workbook_xml_path = os.path.join(temp_dir, "xl", "workbook.xml")
        rels_path = os.path.join(temp_dir, "xl", "_rels", "workbook.xml.rels")
        rels_map = get_relationship_mapping(rels_path)
        sheet_mapping = get_sheet_mapping(workbook_xml_path, rels_map)

        # For each sheet in sheets_to_extract, save out the full XML.
        for sheet_name in sheets_to_extract:
            if sheet_name in sheet_mapping:
                sheet_rel_path = sheet_mapping[sheet_name]
                src_path = os.path.join(temp_dir, sheet_rel_path)
                if os.path.exists(src_path):
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Create an output filename that includes the sheet name.
                    out_filename = sheet_name.replace(" ", "_") + "_" + os.path.basename(sheet_rel_path) + ".txt"
                    out_path = os.path.join(output_folder, out_filename)
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Extracted XML for sheet '{sheet_name}' to {out_path}")
                else:
                    print(f"Sheet file {src_path} does not exist.")
            else:
                print(f"Sheet '{sheet_name}' not found in workbook.")
    finally:
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")

if __name__ == "__main__":
    # Path to the updated Excel file.
    xlsx_path = os.path.join('..', 'output_docs', 'CP_template_metadata_preserved.xlsx')
    # Output folder where the XML files will be saved.
    output_folder = os.path.join('..', 'json_output')
    # Specify the sheet names you want to inspect.
    sheets_to_extract = ["3 - Instructional Design", "3 - Summary", "checks"]
    extract_xml_files(xlsx_path, output_folder, sheets_to_extract)
