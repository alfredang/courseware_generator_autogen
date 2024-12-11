import streamlit as st
import nest_asyncio
import os
import json
from llama_index.llms.openai import OpenAI as llama_openai
from openai import OpenAI
from llama_index.core import (
    Settings,
    StorageContext,
    SummaryIndex,
    load_index_from_storage,
)
from docxtpl import DocxTemplate
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_parse import LlamaParse
import Assessment.utils.utils as utils
from Assessment.utils.agentic_CS import generate_cs
from Assessment.utils.agentic_PP import generate_pp
from Assessment.utils.agentic_SAQ import generate_saq
from Assessment.utils.pydantic_models import FacilitatorGuideExtraction

OPENAI_API_KEY = os.getenv('TERTIARY_INFOTECH_API_KEY') 
LLAMA_API_KEY = os.getenv('LLAMA_CLOUD_API_KEY')

llm_config={
    "config_list": [
        {
            'model': "gpt-4o-mini",
            'api_key': OPENAI_API_KEY,
        },
    ],
    "timeout": 300,
}

def parse_fg(fg_path):
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

def parse_slides(slides_path):
    nest_asyncio.apply()
    
    embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=OPENAI_API_KEY)
    llm = llama_openai(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

    Settings.embed_model = embed_model
    Settings.llm = llm
    
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

def generate_documents(context: dict, assessment_type: str, output_dir: str) -> dict:
    """
    Generate the question paper and answer paper for the given context and type.

    Parameters:
    - context (dict): The data for the assessment (course title, type, questions, etc.).
    - type (int): The assessment type (1 for Ability-based, 2 for Knowledge-based).
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
            {
                **question,
                "answer": None,  # Remove answers for the question document
            }
            for question in context.get("questions", [])
        ]
    }

    # Render both templates
    answer_doc.render(context)  # Render with answers
    question_doc.render(question_context)  # Render without answers

    # Save the documents to the output directory
    files = {
        "QUESTION": os.path.join(output_dir, f"{assessment_type} - {context['course_title']} - v1.docx"),
        "ANSWER": os.path.join(output_dir, f"Answers to {assessment_type} - {context['course_title']} - v1.docx")
    }
    question_doc.save(files["QUESTION"])
    answer_doc.save(files["ANSWER"])

    return files  # Return paths to the generated documents

# Streamlit app
def app():
    # Enable wide mode for the layout
    st.title("📄 Assessment Generator")

    st.write("Upload your Facilitator Guide (.docx) and Trainer Slide Deck (.pdf) to generate assessments.")

    # File upload
    fg_doc_file = st.file_uploader("Upload Facilitator Guide (.docx)", type=["docx"])
    slide_deck_file = st.file_uploader("Upload Trainer Slide Deck (.pdf)", type=["pdf"])

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

    # Button to generate assessments
    if st.button("Generate Assessments"):
        # Validity checks
        if not fg_doc_file:
            st.error("❌ Please upload the Facilitator Guide (.docx) file.")
        elif not slide_deck_file:
            st.error("❌ Please upload the Trainer Slide Deck (.pdf) file.")
        elif not (saq or pp or cs):
            st.error("❌ Please select at least one assessment type to generate.")
        else:
            # If all inputs are valid
            st.success("✅ All inputs are valid. Proceeding with assessment generation...")
            # Placeholder for assessment generation logic
            fg_filepath = utils.save_uploaded_file(fg_doc_file, "data")
            slides_filepath = utils.save_uploaded_file(slide_deck_file, "data")

            try:
                with st.spinner("Parsing FG Document..."):
                    parsed_fg = parse_fg(fg_filepath)
                    st.json(parsed_fg)
                    st.success("✅ Successfully parsed the Facilitator Guide.")
            except Exception as e:
                st.error(f"Error extracting Course Proposal: {e}")
            
            try:
                with st.spinner("Parsing Slide Deck..."):
                    index = parse_slides(slides_filepath)
                    st.success("✅ Successfully parsed the Slide Deck.")
            except Exception as e:
                st.error(f"Error parsing slides: {e}")

            try:
                with st.spinner("Generating Assessments..."):
                    generated_files = {}
                    for assessment_type in selected_types:
                        if assessment_type == "WA (SAQ)":
                            st.info("Short Answer Questions (SAQ) assessment type is not yet supported.")
                            context = generate_saq(parsed_fg, index, llm_config)
                            files = generate_documents(
                                context=context, 
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            generated_files[assessment_type] = files
                        elif assessment_type == "PP":
                            st.info("Practical Performance (PP) assessment type is not yet supported.")
                            # context = generate_pp(parsed_fg, index, llm_config)
                            # files = generate_documents(
                            #     context=context, 
                            #     assessment_type=assessment_type,
                            #     output_dir="output"
                            # )
                            # generated_files[assessment_type] = files
                        elif assessment_type == "CS":
                            context = generate_cs(parsed_fg, index, llm_config)
                            files = generate_documents(
                                context=context, 
                                assessment_type=assessment_type,
                                output_dir="output"
                            )
                            generated_files[assessment_type] = files
                    if generated_files:
                        st.success(f"✅ Successfully generated assessments. \n Output files saved in the 'output' directory. {generated_files}")
                    else:
                        st.error("❌ Error generating assessments.")
            except Exception as e:
                st.error(f"Error generating assessments: {e}")

