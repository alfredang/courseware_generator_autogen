"""
File: assessment_generation.py

===============================================================================
Assessment Generator Module
===============================================================================
Description:
    This module implements a Streamlit-based web application that generates
    assessment documents (e.g., Question and Answer papers) from provided input
    documents. It processes a Facilitator Guide (FG) document and a Trainer Slide
    Deck (PDF) to extract structured data, which is then used to generate assessments
    for various types of tests such as Short Answer Questions (SAQ), Practical
    Performance (PP), and Case Study (CS).

Main Functionalities:
    1. Session State Initialization:
       - Sets up key variables in Streamlit's session_state to maintain state
         across app interactions, including parsed indexes, extracted FG data,
         and generated assessment files.

    2. Helper Functions for Document Processing:
       - get_text_nodes(json_list):
         Extracts text nodes from parsed slide pages.
       - get_page_nodes(docs, separator="\n---\n"):
         Splits each document into page nodes based on a separator.
       - get_pdf_page_count(pdf_path):
         Returns the total number of pages in a PDF using pymupdf.

    3. Facilitator Guide (FG) Parsing and Interpretation:
       - parse_fg(fg_path, LLAMA_API_KEY):
         Parses a Facilitator Guide document using LlamaParse to produce a JSON
         representation of its contents.
       - interpret_fg(fg_data, model_client):
         Uses an AI assistant (via OpenAIChatCompletionClient) to extract and
         structure key information from the FG document based on a predefined JSON
         schema.

    4. Slide Deck Parsing:
       - parse_slides(slides_path, LLAMA_CLOUD_API_KEY, LVM_API_KEY, LVM_NAME, premium_mode=False):
         Processes the Trainer Slide Deck PDF to extract text nodes, optionally
         applying premium parsing instructions if enabled. The parsed content is
         indexed using a vector store for subsequent query operations.

    5. Assessment Document Generation:
       - _ensure_list(answer):
         Utility to guarantee that assessment answers are always returned as a list.
       - generate_documents(context, assessment_type, output_dir):
         Generates both question and answer documents for a given assessment type
         using docxtpl templates. The generated files are saved temporarily and later
         zipped for download.

    6. Streamlit Web Application (app function):
       - Provides a step-by-step user interface for:
           a. Uploading the Facilitator Guide (.docx) and Trainer Slide Deck (.pdf).
           b. Selecting additional parsing options (e.g., Premium Parsing).
           c. Parsing the documents to extract structured data.
           d. Generating assessments (SAQ, PP, CS) based on user selections.
           e. Downloading the generated assessment files as a ZIP archive.
           f. Resetting session data to start over if needed.

Dependencies:
    - Core Libraries:
        • os, io, zipfile, tempfile, json, asyncio, copy (deepcopy)
    - Streamlit:
        • streamlit (for building the web application interface)
    - PDF and Document Parsing:
        • pymupdf (for PDF page count and processing)
        • llama_parse (for parsing documents using LlamaCloud services)
        • docxtpl (for generating and rendering Word document templates)
    - AI and LLM Integration:
        • llama_index (for indexing and processing text nodes)
        • llama_index.llms.openai (for integrating OpenAI models)
        • autogen_agentchat & autogen_core (for structured data extraction using AI)
        • autogen_ext.models.openai (for OpenAIChatCompletionClient)
    - Others:
        • nest_asyncio (to support nested asyncio loops)
        • Assessment.utils and utils.helper (for additional helper functions and model configurations)
        • pymupdf (for handling PDF files)

Usage:
    - Ensure that all external dependencies are installed and that API keys (e.g.,
      LLAMA_CLOUD_API_KEY, OPENAI_API_KEY, LVM_API_KEY) are configured in st.secrets.
    - Run the module via Streamlit using:
          streamlit run <this_file.py>
    - Follow the on-screen instructions:
          1. Upload the Facilitator Guide and Trainer Slide Deck.
          2. Choose parsing options and initiate document parsing.
          3. Select the type(s) of assessments to generate.
          4. Download the generated assessments as a ZIP archive.
          5. Optionally, reset course data to start a new session.

Author: 
    Derrick Lim
Date:
    4 March 2025

Notes:
    - The module integrates asynchronous processing for document parsing and data
      extraction. Ensure that the environment supports asyncio and related libraries.
    - Premium Parsing mode offers enhanced extraction features; enable it only if the
      required vendor services (LVM) are properly configured.
    - The generated assessments are stored temporarily and packaged into a ZIP file
      for ease of download. Clean-up of temporary files is handled automatically.
===============================================================================
"""

import streamlit as st
import nest_asyncio
import os
import io
import zipfile
import asyncio
import json
import pymupdf
import tempfile
from copy import deepcopy
from llama_index.llms.openai import OpenAI as llama_openai
from llama_index.core import (
    Settings,
    VectorStoreIndex,
)
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import MarkdownElementNodeParser
from docxtpl import DocxTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_parse import LlamaParse
import Assessment.utils.utils as utils
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_agentchat.agents import AssistantAgent
from Assessment.utils.agentic_CS import generate_cs
from Assessment.utils.agentic_PP import generate_pp
from Assessment.utils.agentic_SAQ import generate_saq
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from Assessment.utils.model_configs import MODEL_CHOICES, get_model_config
from autogen_ext.models.openai import OpenAIChatCompletionClient
from utils.helper import parse_json_content

################################################################################
# Initialize session_state keys at the top of the script.
################################################################################
if 'index' not in st.session_state:
    st.session_state['index'] = None
if 'fg_data' not in st.session_state:
    st.session_state['fg_data'] = None
if 'saq_output' not in st.session_state:
    st.session_state['saq_output'] = None
if 'pp_output' not in st.session_state:
    st.session_state['pp_output'] = None
if 'cs_output' not in st.session_state:
    st.session_state['cs_output'] = None
if "premium_parsing" not in st.session_state:
    st.session_state["premium_parsing"] = False
if 'assessment_generated_files' not in st.session_state:
    st.session_state['assessment_generated_files'] = {}
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = "Gemini-Pro-2.5-Exp-03-25"

################################################################################
# Helper function for robust text extraction from slide pages.
################################################################################
def get_text_nodes(json_list):
    """Extract text nodes from parsed slides"""
    text_nodes = []
    for page in json_list:
        text_node = TextNode(text=page["md"], metadata={"page": page["page"]})
        text_nodes.append(text_node)
    return text_nodes

def get_page_nodes(docs, separator="\n---\n"):
    """Split each document into page node, by separator."""
    nodes = []
    for doc in docs:
        doc_chunks = doc.text.split(separator)
        for doc_chunk in doc_chunks:
            node = TextNode(
                text=doc_chunk,
                metadata=deepcopy(doc.metadata),
            )
            nodes.append(node)
    return nodes

def get_pdf_page_count(pdf_path):
    # Open the PDF file
    doc = pymupdf.open(pdf_path)
    # Get the total number of pages
    total_pages = doc.page_count
    doc.close()
    return total_pages

################################################################################
# Parse Facilitator Guide Document
################################################################################
def parse_fg(fg_path, LLAMA_API_KEY):
    parser = LlamaParse(
        api_key=LLAMA_API_KEY,
        result_type="markdown",
        fast_mode=True,
        num_workers=8
    )
    parsed_content = parser.get_json_result(fg_path)
    return json.dumps(parsed_content)

async def interpret_fg(fg_data, model_client):
    interpreter = AssistantAgent(
        name="Interpreter",
        model_client=model_client,
        system_message=f"""
        You are an expert at structured data extraction. Extract the following details from the FG Document:
        - Course Title
        - TSC Proficiency Level
        - Learning Units (LUs):
            * Name of the Learning Unit
            * Topics in the Learning Unit:
                - Name of the Topic
                - Description of the Topic (bullet points or sub-topics)
                - Full Knowledge Statements associated with the topic, including their identifiers and text (e.g., K1: Range of AI applications)
                - Full Ability Statements associated with the topic, including their identifiers and text (e.g., A1: Analyze algorithms in the AI applications)
            * Learning Outcome (LO) for each Learning Unit
        - Assessment Types and Durations:
            * Extract assessment types and their durations in the format:
                {{"code": "WA-SAQ", "duration": "1 hr"}}
                {{"code": "PP", "duration": "0.5 hr"}}
                {{"code": "CS", "duration": "30 mins"}}
            * Interpret abbreviations of assessment methods to their correct types (e.g., "WA-SAQ," "PP," "CS").

            Use this JSON schema:
            {json.dumps(FacilitatorGuideExtraction.model_json_schema(), indent=2)}
        """
    )

    agent_task = f"""
    Please extract and structure the following data: {fg_data}.
    **Return the extracted information as a complete JSON dictionary containing the specified fields. Do not truncate or omit any data. Include all fields and their full content. Do not use '...' or any placeholders to replace data.**
    Simply return the JSON dictionary object directly.
    """

    # Process sample input
    response = await interpreter.on_messages(
        [TextMessage(content=agent_task, source="user")], CancellationToken()
    )
    if not response or not response.chat_message:
        return "No content found in the agent's last message."

    context = parse_json_content(response.chat_message.content)
    return context

################################################################################
# Parse Slide Deck Document
################################################################################
def parse_slides(slides_path, LLAMA_CLOUD_API_KEY, LVM_API_KEY, LVM_NAME, premium_mode=False,):
    nest_asyncio.apply()

    total_pages = get_pdf_page_count(slides_path)
    target_pages = f"17-{total_pages - 6}"

    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

    embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
    llm = llama_openai(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

    Settings.embed_model = embed_model
    Settings.llm = llm

    if premium_mode:
        parsing_instruction = """
        You are given training slide materials for a course. Extract and structure the content while preserving the correct reading order.

        - **Text Extraction:** Maintain formatting (headings, bullet points, emphasis).
        - **Graph Processing:** Describe graphs and extract data in a 2D table.
        - **Schematic Diagrams:** List all components and their connections.
        - **Tables & Lists:** Keep original structure and accuracy.
        - **Equations & Symbols:** Format equations properly.
        - **Images & Figures:** Provide descriptive captions.
        - **Best Practices:** Ensure logical order, markdown formatting, and consistency.
        """

        parser = LlamaParse(
            result_type="markdown",
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name=LVM_NAME,
            vendor_multimodal_api_key=LVM_API_KEY,
            invalidate_cache=True,
            verbose=True,
            num_workers=8,
            target_pages=target_pages,
            parsing_instruction=parsing_instruction
        )

        json_objs = parser.get_json_result(slides_path)
        json_list = json_objs[0]["pages"]
        docs = get_text_nodes(json_list)
        index = VectorStoreIndex(docs)
        return index
  
    else:
        documents = LlamaParse(
            result_type="markdown", 
            verbose=True,
            num_workers=8,
            target_pages=target_pages,
            invalidate_cache=True,
            api_key=LLAMA_CLOUD_API_KEY
        ).load_data(slides_path)
        page_nodes = get_page_nodes(documents)
        node_parser = MarkdownElementNodeParser(
           llm=llm, num_workers=8
        )
        nodes = node_parser.get_nodes_from_documents(documents)
        base_nodes, objects = node_parser.get_nodes_and_objects(nodes)
        index = VectorStoreIndex(nodes=base_nodes + objects + page_nodes)
        return index

################################################################################
# Utility function to ensure answers are always a list.
################################################################################
def _ensure_list(answer):
    if isinstance(answer, list):
        return answer
    elif isinstance(answer, str):
        return [answer]
    return []

################################################################################
# Generate documents (Question and Answer papers)
################################################################################
def generate_documents(context: dict, assessment_type: str, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    TEMPLATES = {
        "QUESTION": f"Assessment/utils/Templates/(Template) {assessment_type} - Course Title - v1.docx",
        "ANSWER": f"Assessment/utils/Templates/(Template) Answer to {assessment_type} - Course Title - v1.docx"
    }
    qn_template = TEMPLATES["QUESTION"]
    ans_template = TEMPLATES["ANSWER"]
    question_doc = DocxTemplate(qn_template)
    answer_doc = DocxTemplate(ans_template)
    answer_context = {
        **context,
        "questions": [
            {**question, "answer": _ensure_list(question.get("answer"))}
            for question in context.get("questions", [])
        ]
    }
    question_context = {
        **context,
        "questions": [
            {**question, "answer": None}
            for question in context.get("questions", [])
        ]
    }
    answer_doc.render(answer_context, autoescape=True)
    question_doc.render(question_context, autoescape=True)
    question_tempfile = tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{assessment_type}_Questions.docx"
    )
    answer_tempfile = tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{assessment_type}_Answers.docx"
    )
    question_doc.save(question_tempfile.name)
    answer_doc.save(answer_tempfile.name)
    return {
        "ASSESSMENT_TYPE": assessment_type,
        "QUESTION": question_tempfile.name,
        "ANSWER": answer_tempfile.name
    }

################################################################################
# Streamlit app
################################################################################
def app():
    st.title("📄 Assessment Generator")
    
    st.subheader("Model Selection")
    model_choice = st.selectbox(
        "Select LLM Model:",
        options=list(MODEL_CHOICES.keys()),
        index=0  # default: "GPT-4o Mini (Default)"
    )
    st.session_state['selected_model'] = model_choice

    st.subheader("Step 1: Upload Relevant Documents")
    st.write("Upload your Facilitator Guide (.docx) and Trainer Slide Deck (.pdf) to generate assessments.")
    fg_doc_file = st.file_uploader("Upload Facilitator Guide (.docx)", type=["docx"])
    slide_deck_file = st.file_uploader("Upload Trainer Slide Deck (.pdf)", type=["pdf"])
    
    LLAMA_API_KEY = st.secrets["LLAMA_CLOUD_API_KEY"]

    selected_config = get_model_config(st.session_state['selected_model'])
    api_key = selected_config["config"].get("api_key")
    if not api_key:
        st.error("API key for the selected model is not provided.")
        return
    model_name = selected_config["config"]["model"]
    temperature = selected_config["config"].get("temperature", 0)
    base_url = selected_config["config"].get("base_url", None)
    llama_name = selected_config["config"].get("llama_name", None)

    # Extract model_info from the selected configuration (if provided)
    model_info = selected_config["config"].get("model_info", None)

    # Conditionally set response_format: use structured output only for valid OpenAI models.
    if st.session_state['selected_model'] in ["DeepSeek-V3", "Gemini-Pro-2.5-Exp-03-25"]:
        fg_response_format = None  # DeepSeek and Gemini might not support structured output this way.
    else:
        fg_response_format = FacilitatorGuideExtraction  # For structured extraction

    structured_model_client = OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key,
        temperature=temperature,
        base_url=base_url,
        response_format=fg_response_format,
        model_info=model_info,
    )

    model_client = OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key,
        temperature=temperature,
        base_url=base_url,
        model_info=model_info,
    )

    st.subheader("Step 2: Parse Documents")
    st.write("Select additional parsing options:")
    premium_parsing = st.checkbox("Premium Parsing", value=False)
    if st.button("Parse Documents"):
        if not fg_doc_file or not slide_deck_file:
            st.error("❌ Please upload both the Facilitator Guide and Trainer Slide Deck.")
            return

        st.session_state['premium_parsing'] = premium_parsing
        LLAMA_API_KEY = st.secrets["LLAMA_CLOUD_API_KEY"]
        
        # Initialize variables before the try block
        fg_filepath = None
        slides_filepath = None
        
        try:
            # Save uploaded files
            fg_filepath = utils.save_uploaded_file(fg_doc_file, "data")
            slides_filepath = utils.save_uploaded_file(slide_deck_file, "data")

            with st.spinner("Parsing FG Document..."):
                fg_data = parse_fg(fg_filepath, LLAMA_API_KEY)
                st.session_state['fg_data'] = asyncio.run(interpret_fg(fg_data, structured_model_client))
                st.success("✅ Successfully parsed the Facilitator Guide.")
        
            with st.spinner("Parsing Slide Deck..."):
                st.session_state['index'] = parse_slides(
                    slides_filepath,
                    LLAMA_API_KEY,
                    api_key,
                    llama_name,
                    premium_parsing,
                )
                st.success("✅ Successfully parsed the Slide Deck.")

        except Exception as e:
            st.error(f"Error parsing documents: {e}")

        finally:
            # Ensure variables are not None before trying to delete
            if fg_filepath and os.path.exists(fg_filepath):
                os.remove(fg_filepath)
            if slides_filepath and os.path.exists(slides_filepath):
                os.remove(slides_filepath)

    st.subheader("Step 3: Generate Assessments")
    st.write("Select the type of assessment to generate:")
    saq = st.checkbox("Short Answer Questions (SAQ)")
    pp = st.checkbox("Practical Performance (PP)")
    cs = st.checkbox("Case Study (CS)")

    if st.button("Generate Assessments"):
        st.session_state['assessment_generated_files'] = {}

        if not st.session_state.get('fg_data') or not st.session_state.get('index'):
            st.error("❌ Please parse the documents first.")
            return
        else:
            selected_types = []
            if saq:
                selected_types.append("WA (SAQ)")
            if pp:
                selected_types.append("PP")
            if cs:
                selected_types.append("CS")
            if not selected_types:
                st.error("❌ Please select at least one assessment type to generate.")
                return
            
            st.success("✅ Proceeding with assessment generation...")
            try:
                with st.spinner("Generating Assessments..."):
                    index = st.session_state['index']
                    for assessment_type in selected_types:
                        if assessment_type == "WA (SAQ)":
                            saq_context = asyncio.run(generate_saq(st.session_state['fg_data'], index, model_client, premium_parsing))
                            st.success("✅ Successfully retrieved SAQ context")
                            files = generate_documents(saq_context, assessment_type, "output")
                            st.session_state['assessment_generated_files'][assessment_type] = files
                        elif assessment_type == "PP":
                            pp_context = asyncio.run(generate_pp(st.session_state['fg_data'], index, model_client, premium_parsing))
                            files = generate_documents(pp_context, assessment_type, "output")
                            st.session_state['assessment_generated_files'][assessment_type] = files
                        elif assessment_type == "CS":
                            cs_context = asyncio.run(generate_cs(st.session_state['fg_data'], index, model_client, premium_parsing))
                            files = generate_documents(cs_context, assessment_type, "output")
                            st.session_state['assessment_generated_files'][assessment_type] = files

                if st.session_state['assessment_generated_files']:
                    st.success("✅ Assessments successfully generated!")

            except Exception as e:
                st.error(f"Error generating assessments: {e}")

    generated_files = st.session_state.get('assessment_generated_files', {})
    # Check if any assessment type has a valid QUESTION or ANSWER file
    if generated_files and any(
        ((file_paths.get('QUESTION') and os.path.exists(file_paths.get('QUESTION'))) or 
        (file_paths.get('ANSWER') and os.path.exists(file_paths.get('ANSWER'))))
        for file_paths in generated_files.values()
    ):
        course_title = "Course Title"
        # If fg_data is available, update course_title accordingly.
        if st.session_state.get('fg_data'):
            course_title = st.session_state['fg_data'].get("course_title", "Course Title")
        
        # Create an in-memory ZIP file containing all available assessment documents.
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for assessment_type, file_paths in generated_files.items():
                q_path = file_paths.get('QUESTION')
                a_path = file_paths.get('ANSWER')
                
                if q_path and os.path.exists(q_path):
                    q_file_name = f"{assessment_type} - {course_title}.docx"
                    zipf.write(q_path, arcname=q_file_name)
                
                if a_path and os.path.exists(a_path):
                    a_file_name = f"Answer to {assessment_type} - {course_title}.docx"
                    zipf.write(a_path, arcname=a_file_name)
        
        # Reset the buffer's position to the beginning
        zip_buffer.seek(0)
        
        st.download_button(
            label="Download All Assessments (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="assessments.zip",
            mime="application/zip"
        )
    else:
        st.info("No files have been generated yet. Please generate assessments first.")

    ############################################################################
    # Reset Button at the Bottom
    ############################################################################
    if st.button("Reset Course Data", type="primary"):
        st.session_state['index'] = None
        st.session_state['fg_data'] = None
        st.session_state['assessment_generated_files'] = {}
        st.session_state['saq_output'] = None
        st.session_state['pp_output'] = None
        st.session_state['cs_output'] = None
        st.success("Course data has been reset.")