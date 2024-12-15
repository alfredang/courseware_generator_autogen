import streamlit as st
import nest_asyncio
import os
import json
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

                    Return the output in a JSON format that matches the schema provided:
                    {
                        "course_title": "string",
                        "tsc_proficiency_level": "string",
                        "learning_units": [
                            {
                                "name": "string",
                                "topics": [
                                    {
                                        "name": "string",
                                        "subtopics": ["string"],
                                        "tsc_knowledges": [
                                            {"id": "string", "text": "string"}
                                        ],
                                        "tsc_abilities": [
                                            {"id": "string", "text": "string"}
                                        ]
                                    }
                                ],
                                "learning_outcome": "string"
                            }
                        ],
                        "assessments": [
                            {"code": "string", "duration": "string"}
                        ]
                    }
                    """
                ),
            },
            {"role": "user", "content": json.dumps(parsed_content)},
        ],
        response_format=FacilitatorGuideExtraction,
    )
    return completion.choices[0].message.parsed

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
        
        image_dicts = slides_parser.get_images(md_json_objs, download_path="data_images")
        text_nodes = utils.get_text_nodes(md_json_list, image_dir="data_images")

        if not os.path.exists("storage_nodes_summary"):
            index = SummaryIndex(text_nodes)
            # save index to disk
            index.set_index_id("summary_index")
            index.storage_context.persist("./storage_nodes_summary")
            return index
        else:
            # rebuild storage context
            storage_context = StorageContext.from_defaults(persist_dir="storage_nodes_summary")
            # load index
            index = load_index_from_storage(storage_context, index_id="summary_index")
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

        # --- 3. Parse Markdown structure with MarkdownElementNodeParser ---
        # This creates a hierarchical parse of tables, headings, lists, etc.
        node_parser = MarkdownElementNodeParser(
            llm=llama_openai(model_name="gpt-4o-mini"),  # or "gpt-4o-mini" if available
            num_workers=8,
            include_metadata=True
        )
        # node_parser expects Document objects
        parsed_nodes = node_parser.get_nodes_from_documents(documents)
        base_nodes, objects = node_parser.get_nodes_and_objects(parsed_nodes)

        # --- 4. Combine raw page nodes + structured parse nodes ---
        # This approach stores both the “raw markdown text” nodes and the “parsed objects”
        # in a single index to allow flexible retrieval strategies.
        combined_nodes = base_nodes + objects + page_nodes

        # --- 5. Create a VectorStoreIndex ---
        # By default, VectorStoreIndex is built on these combined nodes.
        index = VectorStoreIndex(nodes=combined_nodes)
        return index

def generate_documents(context: dict, assessment_type: str, output_dir: str) -> dict:
    """
    Generate the question paper and answer paper for the given context and type.

    Parameters:
    - context (dict): The data for the assessment (course title, type, questions, etc.).
    - assessment_type (str): The assessment type (e.g., 'Ability-based', 'Knowledge-based').
    - output_dir (str): Directory where the generated documents will be saved.

    Returns:
    - dict: Paths to the generated documents (question and answer papers).
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load templates
    TEMPLATES = {
        "QUESTION": f"Assessment/Templates/(Template) {assessment_type} - Course Title - v1.docx",
        "ANSWER": f"Assessment/Templates/(Template) Answer to {assessment_type} - Course Title - v1.docx"
        }

    qn_template = TEMPLATES["QUESTION"]
    ans_template = TEMPLATES["ANSWER"]
    question_doc = DocxTemplate(qn_template)
    answer_doc = DocxTemplate(ans_template)
    
    # Prepare context for the question paper by creating a copy of the context without answers
    question_context = {
        **context,
        "questions": [
            {**question, "answer": None} for question in context.get("questions", [])
        ]
    }


    # Render both templates
    answer_doc.render(context)  # Render with answers
    question_doc.render(question_context)  # Render without answers

    # Create temporary files for the question and answer documents
    question_tempfile = tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{assessment_type}_Questions.docx"
    )
    answer_tempfile = tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{assessment_type}_Answers.docx"
    )

    # Save the rendered documents to the temporary files
    question_doc.save(question_tempfile.name)
    answer_doc.save(answer_tempfile.name)

    return {
        "ASSESSMENT_TYPE": assessment_type,
        "QUESTION": question_tempfile.name,
        "ANSWER": answer_tempfile.name
    }

# Streamlit app
def app():
    # Enable wide mode for the layout
    st.title("📄 Assessment Generator")

    st.write("Upload your Facilitator Guide (.docx) and Trainer Slide Deck (.pdf) to generate assessments.")

    # File upload
    fg_doc_file = st.file_uploader("Upload Facilitator Guide (.docx)", type=["docx"])
    slide_deck_file = st.file_uploader("Upload Trainer Slide Deck (.pdf)", type=["pdf"])
    
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    LLAMA_API_KEY = st.secrets["LLAMA_CLOUD_API_KEY"]

    llm_config={
        "config_list": [
            {
                'model': "gpt-4o-mini",
                'api_key': OPENAI_API_KEY,
            },
        ],
        "timeout": 300,
    }
    # Assessment type selection
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

    is_multimodal = st.toggle("Enable Multimodal RAG", False)

    if is_multimodal:
        st.warning("⚠️ Multimodal RAG may take longer to process.")
    # Button to generate assessments
    if st.button("Generate Assessments"):
        st.session_state['generated_files'] = {}
        st.session_state['processing_done'] = False
        st.session_state['index'] = None
        # Validity checks
        if not fg_doc_file:
            st.error("❌ Please upload the Facilitator Guide (.docx) file.")
        elif not slide_deck_file:
            st.error("❌ Please upload the Trainer Slide Deck (.pdf) file.")
        elif not selected_types:
            st.error("❌ Please select at least one assessment type to generate.")
        else:
            st.success("✅ All inputs are valid. Proceeding with assessment generation...")
            
            # Save uploaded files
            fg_filepath = utils.save_uploaded_file(fg_doc_file, "data")
            slides_filepath = utils.save_uploaded_file(slide_deck_file, "data")

            # Parse FG Document
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
            
            # Parse Slide Deck
            try:
                with st.spinner("Parsing Slide Deck..."):
                    if not st.session_state['index']:
                        st.session_state['index'] = parse_slides(slides_filepath, LLAMA_API_KEY, OPENAI_API_KEY, is_multimodal)
                    index = st.session_state['index']
                    st.success("✅ Successfully parsed the Slide Deck.")
            except Exception as e:
                st.error(f"Error parsing slides: {e}")
                return

            # Generate Assessments for each selected type
            try:
                with st.spinner("Generating Assessments..."):
                    for assessment_type in selected_types:
                        if assessment_type == "WA (SAQ)":
                            print("### GENERATING SAQ ASSESSMENT ###")
                            saq_context = generate_saq(parsed_fg, index, llm_config)
                            files = generate_documents(
                                context=saq_context, 
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            st.session_state['generated_files'][assessment_type] = files
                        elif assessment_type == "PP":
                            print("### GENERATING PP ASSESSMENT ###")
                            pp_context = generate_pp(parsed_fg, index, llm_config)
                            files = generate_documents(
                                context=pp_context, 
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            st.session_state['generated_files'][assessment_type] = files
                        elif assessment_type == "CS":
                            print("### GENERATING CS ASSESSMENT ###")
                            cs_context = generate_cs(parsed_fg, index, llm_config)
                            files = generate_documents(
                                context=cs_context, 
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            st.session_state['generated_files'][assessment_type] = files

                    if st.session_state['generated_files']:
                        st.session_state['processing_done'] = True
                        st.success("✅ Successfully generated assessments. Output files saved in the 'output' directory.")
                    else:
                        st.error("❌ Error generating assessments.")
            except Exception as e:
                st.error(f"Error generating assessments: {e}")

    # Download section
    if st.session_state['processing_done']:
        st.header("Download Generated Documents")

        # Iterate over all generated assessments
        for assessment_type, file_paths in st.session_state['generated_files'].items():
            q_path = file_paths['QUESTION']
            a_path = file_paths['ANSWER']
            course_title = file_paths.get("course_title", "CourseTitle")

            if os.path.exists(q_path):
                with open(q_path, "rb") as f:
                    file_bytes = f.read()
                q_file_name = f"{assessment_type} {course_title} - v1.docx"
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