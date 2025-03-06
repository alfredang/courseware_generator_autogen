# streamlit_app.py
import streamlit as st
from gemini_processor import process_document  # Import from the other file
import os
import tempfile
from PIL import Image
import pytesseract  # For OCR on images

# Set tesseract path (if needed)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Example path
streamlit_path = r'C:\Users\marcu\AppData\Roaming\Python\Python312\Scripts'
if streamlit_path not in os.environ['PATH']:
    os.environ['PATH'] += os.pathsep + streamlit_path

st.title("Gemini Named Entity Extraction")

custom_instructions = st.text_area("Enter your custom instructions for entity extraction:",
                                 "Extract all person names, organizations, and locations.")


uploaded_file = st.file_uploader("Upload a PDF or image file", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    with st.spinner("Processing document..."):
        file_extension = uploaded_file.name.split(".")[-1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_file_path = temp_file.name

        document_text = ""

        if file_extension == "pdf":
            try:
                from pypdf import PdfReader  # Install pypdf: pip install pypdf
                reader = PdfReader(temp_file_path)
                for page in reader.pages:
                    document_text += page.extract_text()
            except Exception as e:
                st.error(f"Error processing PDF: {e}")

        elif file_extension in ["png", "jpg", "jpeg"]:
            try:
                image = Image.open(temp_file_path)
                document_text = pytesseract.image_to_string(image)
            except Exception as e:
                st.error(f"Error processing image: {e}")
        else:
            st.error("Unsupported file type.")

        if document_text:
            extracted_entities = process_document(temp_file_path, custom_instructions)
            st.write("Extracted Entities:")
            st.json(extracted_entities)

        os.remove(temp_file_path) # Clean up the temporary file
