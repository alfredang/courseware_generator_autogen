import streamlit as st
import nest_asyncio
import os
import asyncio
import json
import shutil
import pymupdf
import tempfile
from copy import deepcopy
from llama_index.llms.openai import OpenAI as llama_openai
from openai import OpenAI
from llama_index.core import (
    Settings,
    StorageContext,
    SummaryIndex,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.schema import Document, TextNode
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
from autogen_ext.models.openai import OpenAIChatCompletionClient
from utils.model_configs import MODEL_CHOICES, get_model_config
from utils.helper import parse_json_content

################################################################################
# Initialize session_state keys at the top of the script.
################################################################################
if 'index' not in st.session_state:
    st.session_state['index'] = None
if 'fg_data' not in st.session_state:
    st.session_state['fg_data'] = None
if 'processing_done' not in st.session_state:
    st.session_state['processing_done'] = False
if 'saq_output' not in st.session_state:
    st.session_state['saq_output'] = None
if 'pp_output' not in st.session_state:
    st.session_state['pp_output'] = None
if 'cs_output' not in st.session_state:
    st.session_state['cs_output'] = None
if "premium_parsing" not in st.session_state:
    st.session_state["premium_parsing"] = False
if 'generated_files' not in st.session_state:
    st.session_state['generated_files'] = {}
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = "GPT-4o-Mini"
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
def parse_slides(slides_path, LLAMA_CLOUD_API_KEY, OPENAI_API_KEY, premium_mode=False):
    nest_asyncio.apply()

    total_pages = get_pdf_page_count(slides_path)
    target_pages = f"17-{total_pages - 6}"
    # print(f"Target pages: {target_pages}")

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
            vendor_multimodal_model_name="openai-gpt-4o-mini",
            vendor_multimodal_api_key=OPENAI_API_KEY,
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
            invalidate_cache=True
        ).load_data(slides_path)
        page_nodes = get_page_nodes(documents)
        node_parser = MarkdownElementNodeParser(
           llm=llama_openai(model="gpt-4o-mini"), num_workers=8
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

    # Extract model_info from the selected configuration (if provided)
    model_info = selected_config["config"].get("model_info", None)

    # Conditionally set response_format: use structured output only for valid OpenAI models.
    if st.session_state['selected_model'] in ["DeepSeek", "Gemini"]:
        fg_response_format = None  # DeepSeek and Gemini might not support structured output this way.
    else:
        fg_response_format = FacilitatorGuideExtraction  # For structured CP extractio

    structured_model_client = OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key,
        temperature=temperature,
        base_url=base_url,
        response_format=fg_response_format,  # Only set for valid OpenAI models
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
                if not st.session_state['fg_data']:
                    fg_data = parse_fg(fg_filepath, LLAMA_API_KEY)
                    st.session_state['fg_data'] = asyncio.run(interpret_fg(fg_data, structured_model_client))
                    parsed_fg = st.session_state.get('fg_data')
                st.json(parsed_fg)
                st.success("✅ Successfully parsed the Facilitator Guide.")
        
            with st.spinner("Parsing Slide Deck..."):
                if not st.session_state['index']:
                    st.session_state['index'] = parse_slides(
                        slides_filepath,
                        LLAMA_API_KEY,
                        api_key,
                        premium_parsing
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
        st.session_state['generated_files'] = {}
        st.session_state['processing_done'] = False

        if not st.session_state['fg_data'] or not st.session_state['index']:
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
                            # print(saq_context)
                            st.success("✅ Successfully retrieved SAQ context")
                            files = generate_documents(saq_context, assessment_type, "output")
                            st.session_state['generated_files'][assessment_type] = files
                        elif assessment_type == "PP":
                            print(st.session_state['fg_data'])
                            pp_context = asyncio.run(generate_pp(st.session_state['fg_data'], index, model_client, premium_parsing))
                            files = generate_documents(pp_context, assessment_type, "output")
                            st.session_state['generated_files'][assessment_type] = files
                        elif assessment_type == "CS":
                            cs_context = asyncio.run(generate_cs(st.session_state['fg_data'], index, model_client, premium_parsing))
                            files = generate_documents(cs_context, assessment_type, "output")
                            st.session_state['generated_files'][assessment_type] = files

                if st.session_state['generated_files']:
                    st.session_state['processing_done'] = True
                    st.success("✅ Assessments successfully generated!")

            except Exception as e:
                st.error(f"Error generating assessments: {e}")

    if st.session_state.get('processing_done'):
        st.subheader("Download Generated Documents")
        for assessment_type, file_paths in st.session_state['generated_files'].items():
            q_path = file_paths['QUESTION']
            a_path = file_paths['ANSWER']
            course_title = st.session_state['fg_data'].get("course_title", "Course Title")

            if os.path.exists(q_path):
                with open(q_path, "rb") as f:
                    st.download_button(f"Download {assessment_type} Questions", f.read(), f"{assessment_type} - {course_title}.docx")

            if os.path.exists(a_path):
                with open(a_path, "rb") as f:
                    st.download_button(f"Download {assessment_type} Answers", f.read(), f"Answer to {assessment_type} - {course_title}.docx")