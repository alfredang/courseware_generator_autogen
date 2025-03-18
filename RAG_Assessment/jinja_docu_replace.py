import json
import os
from docxtpl import DocxTemplate

# Load the assessment data
def load_assessment_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        # Remove comments if present (starts with //)
        content = '\n'.join([line for line in file if not line.strip().startswith('//')])
        return json.loads(content)

# Load SAQ and PP assessment data
saq_data = load_assessment_data('output_json/saq_assessment.json')
pp_data = load_assessment_data('output_json/pp_assessment.json')

def prepare_saq_context(data, course_title="Software Configuration Management", duration="1 hr"):
    """Prepare SAQ data for the document template"""
    # Format the questions appropriately
    questions = []
    for q in data.get('questions', []):
        questions.append({
            "knowledge_id": q.get("knowledge_id", ""),
            "question_statement": q.get("question_statement", ""),
            "scenario": q.get("scenario", ""),
            # For answer template only
            "answer": q.get("answer", [])
        })
    
    return {
        "course_title": course_title,
        "duration": duration,
        "questions": questions
    }

def prepare_pp_context(data, course_title="Software Configuration Management", duration="30 mins"):
    """Prepare PP data for the document template"""
    # Extract scenario
    scenario = data.get("scenario", "")
    
    # Format questions
    questions = []
    for q in data.get('questions', []):
        # For PP, convert the nested answer structure
        answer_content = []
        if isinstance(q.get("answer", {}), dict):
            answer_content = q["answer"].get("expected_output", "").split("\n")
        
        questions.append({
            "learning_outcome_id": q.get("learning_outcome_id", ""),
            "question_statement": q.get("question_statement", ""),
            "ability_id": q.get("ability_id", []),
            # For answer template only
            "answer": answer_content
        })
    
    return {
        "course_title": course_title,
        "duration": duration,
        "scenario": scenario,
        "questions": questions
    }

# def generate_assessment_documents(context, assessment_type, output_dir):
#     """Generate assessment documents from the provided context"""
#     os.makedirs(output_dir, exist_ok=True)
    
#     # Define specific template mappings based on assessment type
#     if assessment_type == "PP":
#         TEMPLATES = {
#             "QUESTION": "templates/(Template) CS - Course Title - v1.docx",
#             "ANSWER": "templates/(Template) Answer to CS - Course Title - v1.docx"
#         }
#     elif assessment_type == "WA-SAQ":
#         TEMPLATES = {
#             "QUESTION": "templates/(Template) WA (SAQ) - Course Title - v1.docx",
#             "ANSWER": "templates/(Template) Answer to WA (SAQ) - Course Title - v1.docx"
#         }
#     else:
#         # Fallback to original pattern if needed for other types
#         TEMPLATES = {
#             "QUESTION": f"templates/(Template) {assessment_type} - Course Title - v1.docx",
#             "ANSWER": f"templates/(Template) Answer to {assessment_type} - Course Title - v1.docx"
#         }
    
#     question_doc = DocxTemplate(TEMPLATES["QUESTION"])
#     answer_doc = DocxTemplate(TEMPLATES["ANSWER"])

    
#     # Ensure answers are in list format and prepare contexts
#     answer_context = context.copy()
#     question_context = {
#         **context,
#         "questions": [
#             {**q, "answer": None} for q in context.get("questions", [])
#         ]
#     }
    
#     # Render templates
#     question_doc.render(question_context, autoescape=True)
#     answer_doc.render(answer_context, autoescape=True)
    
#     # Save files with descriptive names
#     question_file = os.path.join(output_dir, f"{assessment_type}_Questions.docx")
#     answer_file = os.path.join(output_dir, f"{assessment_type}_Answers.docx")
    
#     question_doc.save(question_file)
#     answer_doc.save(answer_file)
    
#     return {
#         "ASSESSMENT_TYPE": assessment_type,
#         "QUESTION": question_file,
#         "ANSWER": answer_file
#     }

def generate_assessment_documents(context, assessment_type, output_dir):
    """Generate assessment documents from the provided context"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Get current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define template folder relative to script location
    template_folder = os.path.join(script_dir, "templates")
    
    # Since you only have answer templates right now
    if assessment_type == "PP":
        TEMPLATES = {
            "QUESTION": None,  # Set to None if not available
            "ANSWER": os.path.join(template_folder, "(Template) Answer to CS - Course Title - v1.docx")
        }
    elif assessment_type == "WA-SAQ":
        TEMPLATES = {
            "QUESTION": None,  # Set to None if not available
            "ANSWER": os.path.join(template_folder, "(Template) Answer to WA (SAQ) - Course Title - v1.docx")
        }
    else:
        TEMPLATES = {
            "QUESTION": None,  # Set to None if not available
            "ANSWER": os.path.join(template_folder, f"(Template) Answer to {assessment_type} - Course Title - v1.docx")
        }
    
    # Only process templates that exist
    files_generated = {}
    
    # Process answer template
    if TEMPLATES["ANSWER"] and os.path.exists(TEMPLATES["ANSWER"]):
        answer_doc = DocxTemplate(TEMPLATES["ANSWER"])
        answer_context = context.copy()
        answer_doc.render(answer_context, autoescape=True)
        
        # Save answer file
        answer_file = os.path.join(output_dir, f"{assessment_type}_Answers.docx")
        answer_doc.save(answer_file)
        files_generated["ANSWER"] = answer_file
    else:
        print(f"Warning: Answer template not found at {TEMPLATES['ANSWER']}")
    
    # Process question template (when available)
    if TEMPLATES["QUESTION"] and os.path.exists(TEMPLATES["QUESTION"]):
        question_doc = DocxTemplate(TEMPLATES["QUESTION"])
        question_context = {
            **context,
            "questions": [
                {**q, "answer": None} for q in context.get("questions", [])
            ]
        }
        question_doc.render(question_context, autoescape=True)
        
        # Save question file
        question_file = os.path.join(output_dir, f"{assessment_type}_Questions.docx")
        question_doc.save(question_file)
        files_generated["QUESTION"] = question_file
    
    files_generated["ASSESSMENT_TYPE"] = assessment_type
    return files_generated

def main():
    output_dir = "generated_docs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate SAQ documents
    saq_context = prepare_saq_context(saq_data)
    saq_files = generate_assessment_documents(saq_context, "WA-SAQ", output_dir)
    print(f"SAQ documents generated: {saq_files}")
    
    # Generate PP documents
    pp_context = prepare_pp_context(pp_data)
    pp_files = generate_assessment_documents(pp_context, "PP", output_dir)
    print(f"PP documents generated: {pp_files}")

if __name__ == "__main__":
    main()