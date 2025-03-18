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

def generate_assessment_documents(context, assessment_type, output_dir):
    """Generate assessment documents from the provided context"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Template paths
    TEMPLATES = {
        "QUESTION": f"Assessment/utils/Templates/(Template) {assessment_type} - Course Title - v1.docx",
        "ANSWER": f"Assessment/utils/Templates/(Template) Answer to {assessment_type} - Course Title - v1.docx"
    }
    
    question_doc = DocxTemplate(TEMPLATES["QUESTION"])
    answer_doc = DocxTemplate(TEMPLATES["ANSWER"])
    
    # Ensure answers are in list format and prepare contexts
    answer_context = context.copy()
    question_context = {
        **context,
        "questions": [
            {**q, "answer": None} for q in context.get("questions", [])
        ]
    }
    
    # Render templates
    question_doc.render(question_context, autoescape=True)
    answer_doc.render(answer_context, autoescape=True)
    
    # Save files with descriptive names
    question_file = os.path.join(output_dir, f"{assessment_type}_Questions.docx")
    answer_file = os.path.join(output_dir, f"{assessment_type}_Answers.docx")
    
    question_doc.save(question_file)
    answer_doc.save(answer_file)
    
    return {
        "ASSESSMENT_TYPE": assessment_type,
        "QUESTION": question_file,
        "ANSWER": answer_file
    }

def main():
    output_dir = "RAG_Assessment/generated_docs"
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