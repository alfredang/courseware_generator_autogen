import streamlit as st
import nest_asyncio
import os
import asyncio
import json
import shutil
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
from Assessment.utils.agentic_CS import generate_cs
from Assessment.utils.agentic_PP import generate_pp
from Assessment.utils.agentic_SAQ import generate_saq
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction
from autogen_ext.models.openai import OpenAIChatCompletionClient

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
if 'generated_files' not in st.session_state:
    st.session_state['generated_files'] = {}
if "old_multimodal_value" not in st.session_state:
    st.session_state["old_multimodal_value"] = False
if "prev_multimodal_value" not in st.session_state:
    st.session_state["prev_multimodal_value"] = st.session_state["old_multimodal_value"]

################################################################################
# Helper function for robust text extraction from slide pages.
################################################################################
def get_text_nodes_updated(pages, image_dir):
    nodes = []
    for page in pages:
        # Use .get() to safely access "text", defaulting to an empty string if missing.
        text_content = page.get("text", "")
        if not text_content:
            st.write(f"Warning: Page {page.get('page_number', 'unknown')} is missing the 'text' field.")
        node = TextNode(
            text=text_content,
            metadata={"page_number": page.get("page_number")}
        )
        nodes.append(node)
    return nodes

################################################################################
# Parse Facilitator Guide Document
################################################################################
def parse_fg(fg_path, OPENAI_API_KEY, LLAMA_API_KEY):
    client = OpenAI(api_key=OPENAI_API_KEY)
    parser = LlamaParse(
        api_key=LLAMA_API_KEY,
        result_type="markdown",
        fast_mode=True,
        num_workers=8
    )
    parsed_content = parser.get_json_result(fg_path)
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    """You are an expert at structured data extraction. Extract the following details from the FG Document:
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
                          {"code": "WA-SAQ", "duration": "1 hr"}
                          {"code": "PP", "duration": "0.5 hr"}
                          {"code": "CS", "duration": "30 mins"}
                        * Interpret abbreviations of assessment methods to their correct types (e.g., "WA-SAQ," "PP," "CS").
                    """
                ),
            },
            {"role": "user", "content": json.dumps(parsed_content)},
        ],
        response_format=FacilitatorGuideExtraction,
    )
    return completion.choices[0].message.parsed

################################################################################
# Parse Slide Deck Document
################################################################################
def parse_slides(slides_path, LLAMA_CLOUD_API_KEY, OPENAI_API_KEY, is_multimodal=False):
    nest_asyncio.apply()
    
    embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
    llm = llama_openai(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

    Settings.embed_model = embed_model
    Settings.llm = llm

    if is_multimodal:
        slides_parser = LlamaParse(
            result_type="markdown",
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name="openai-gpt-4o-mini",
            vendor_multimodal_api_key=OPENAI_API_KEY,
            verbose=True,
            fast_mode=True,
            num_workers=8,
        )
        md_json_objs = slides_parser.get_json_result(slides_path)
        md_json_list = md_json_objs[0]["pages"]
        
        os.makedirs("data_images", exist_ok=True)
        image_dicts = slides_parser.get_images(md_json_objs, download_path="data_images")
        # Use our updated function for robust text extraction.
        text_nodes = get_text_nodes_updated(md_json_list, image_dir="data_images")

        if not os.path.exists("storage_nodes_summary"):
            index = SummaryIndex(text_nodes)
            index.set_index_id("summary_index")
            index.storage_context.persist("./storage_nodes_summary")
        else:
            storage_context = StorageContext.from_defaults(persist_dir="storage_nodes_summary")
            index = load_index_from_storage(storage_context, index_id="summary_index")
        
        # Cleanup multimodal directories
        if os.path.exists("data_images"):
            shutil.rmtree("data_images")    
        if os.path.exists("storage_nodes_summary"):
            shutil.rmtree("storage_nodes_summary")
        return index
  
    else:
        documents = LlamaParse(result_type="markdown").load_data(slides_path)
        
        def get_page_nodes(docs, separator="\n---\n"):
            nodes = []
            for doc in docs:
                chunks = doc.text.split(separator)
                for chunk in chunks:
                    node = TextNode(
                        text=chunk,
                        metadata=deepcopy(doc.metadata)
                    )
                    nodes.append(node)
            return nodes

        page_nodes = get_page_nodes(documents, separator="\n---\n")
        node_parser = MarkdownElementNodeParser(
            llm=llama_openai(model_name="gpt-4o-mini"),
            num_workers=8,
            include_metadata=True
        )
        parsed_nodes = node_parser.get_nodes_from_documents(documents)
        base_nodes, objects = node_parser.get_nodes_and_objects(parsed_nodes)
        combined_nodes = base_nodes + objects + page_nodes
        index = VectorStoreIndex(nodes=combined_nodes)
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
        "QUESTION": f"Assessment/Templates/(Template) {assessment_type} - Course Title - v1.docx",
        "ANSWER": f"Assessment/Templates/(Template) Answer to {assessment_type} - Course Title - v1.docx"
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
    st.write("Upload your Facilitator Guide (.docx) and Trainer Slide Deck (.pdf) to generate assessments.")
    fg_doc_file = st.file_uploader("Upload Facilitator Guide (.docx)", type=["docx"])
    slide_deck_file = st.file_uploader("Upload Trainer Slide Deck (.pdf)", type=["pdf"])
    
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    LLAMA_API_KEY = st.secrets["LLAMA_CLOUD_API_KEY"]

    model_client = OpenAIChatCompletionClient(
        model=st.secrets["REPLACEMENT_MODEL"],
        temperature=0,
        api_key=OPENAI_API_KEY
    )

    st.write("Select the type of assessment to generate:")
    saq = st.checkbox("Short Answer Questions (SAQ)")
    pp = st.checkbox("Practical Performance (PP)")
    cs = st.checkbox("Case Study (CS)")
    selected_types = []
    if saq:
        selected_types.append("WA (SAQ)")
    if pp:
        selected_types.append("PP")
    if cs:
        selected_types.append("CS")
    
    # Use the toggle widget to control multimodal RAG.
    current_multimodal_value = st.toggle(
        "Enable Multimodal RAG",
        value=st.session_state["old_multimodal_value"],
        key="old_multimodal_value"
    )
    # If the toggle value has changed compared to its previous value, reset the index.
    if st.session_state["old_multimodal_value"] != st.session_state["prev_multimodal_value"]:
        st.session_state["index"] = None
    st.session_state["prev_multimodal_value"] = st.session_state["old_multimodal_value"]

    if current_multimodal_value:
        st.warning("⚠️ Multimodal RAG may take longer to process.")

    if st.button("Generate Assessments"):
        st.session_state['generated_files'] = {}
        st.session_state['processing_done'] = False

        if not fg_doc_file:
            st.error("❌ Please upload the Facilitator Guide (.docx) file.")
        elif not slide_deck_file:
            st.error("❌ Please upload the Trainer Slide Deck (.pdf) file.")
        elif not selected_types:
            st.error("❌ Please select at least one assessment type to generate.")
        else:
            st.success("✅ All inputs are valid. Proceeding with assessment generation...")
            fg_filepath = utils.save_uploaded_file(fg_doc_file, "data")
            slides_filepath = utils.save_uploaded_file(slide_deck_file, "data")
            
            try:
                with st.spinner("Parsing FG Document..."):
                    if not st.session_state['fg_data']:
                        st.session_state['fg_data'] = parse_fg(fg_filepath, OPENAI_API_KEY, LLAMA_API_KEY)
                    parsed_fg = st.session_state['fg_data']
                    st.json(parsed_fg)
                    st.success("✅ Successfully parsed the Facilitator Guide.")
            except Exception as e:
                st.error(f"Error extracting FG Document: {e}")
                return
            
            try:
                with st.spinner("Parsing Slide Deck..."):
                    if not st.session_state['index']:
                        st.session_state['index'] = parse_slides(
                            slides_filepath,
                            LLAMA_API_KEY,
                            OPENAI_API_KEY,
                            current_multimodal_value
                        )
                    index = st.session_state['index']
                    st.success("✅ Successfully parsed the Slide Deck.")
            except Exception as e:
                st.error(f"Error parsing slides: {e}")
                return
            
            try:
                with st.spinner("Generating Assessments..."):
                    for assessment_type in selected_types:
                        if assessment_type == "WA (SAQ)":
                            print("### GENERATING SAQ ASSESSMENT ###")
                            saq_context = asyncio.run(generate_saq(parsed_fg, index, model_client))
                            files = generate_documents(
                                context=saq_context,
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            st.session_state['generated_files'][assessment_type] = files
                        elif assessment_type == "PP":
                            print("### GENERATING PP ASSESSMENT ###")
                            pp_context = asyncio.run(generate_pp(parsed_fg, index, model_client))
                            files = generate_documents(
                                context=pp_context,
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            st.session_state['generated_files'][assessment_type] = files
                        elif assessment_type == "CS":
                            print("### GENERATING CS ASSESSMENT ###")
                            cs_context = asyncio.run(generate_cs(parsed_fg, index, model_client))
                            files = generate_documents(
                                context=cs_context,
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            st.session_state['generated_files'][assessment_type] = files
                    if st.session_state.get('generated_files'):
                        st.session_state['processing_done'] = True
                        st.success("✅ Successfully generated assessments. Output files saved in the 'output' directory.")
                    else:
                        st.error("❌ Error generating assessments.")
            except Exception as e:
                st.error(f"Error generating assessments: {e}")
            finally:
                if os.path.exists(fg_filepath):
                    os.remove(fg_filepath)
                if os.path.exists(slides_filepath):
                    os.remove(slides_filepath)
    
    if st.session_state.get('processing_done'):
        st.subheader("Download Generated Documents")
        for assessment_type, file_paths in st.session_state.get('generated_files').items():
            q_path = file_paths['QUESTION']
            a_path = file_paths['ANSWER']
            course_title = dict(st.session_state['fg_data']).get("course_title", "Course Title")
            if os.path.exists(q_path):
                with open(q_path, "rb") as f:
                    file_bytes = f.read()
                q_file_name = f"{assessment_type} - {course_title} - v1.docx"
                st.download_button(
                    label=f"Download {assessment_type} Questions",
                    data=file_bytes,
                    file_name=q_file_name,
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            if os.path.exists(a_path):
                with open(a_path, "rb") as f:
                    file_bytes = f.read()
                a_file_name = f"Answer to {assessment_type} {course_title} - v1.docx"
                st.download_button(
                    label=f"Download {assessment_type} Answers",
                    data=file_bytes,
                    file_name=a_file_name,
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )

