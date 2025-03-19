import os
import asyncio
import json
from redisvl.schema import IndexSchema
from llama_index.vector_stores.redis import RedisVectorStore
from llama_index.core import VectorStoreIndex

from evaluation_schema import define_custom_schema
# from retrieval_workflow import define_custom_schema
from config_loader import load_shared_resources
from evaluation.retrieval_metrics import evaluate_retrieval_quality
from evaluation.assessment_metrics import evaluate_educational_quality
from evaluation.visualisation import create_evaluation_report

def transform_assessment_data(saq_path, pp_path=None):
    """Transform the SAQ and PP assessment data into the format expected by the evaluation metrics."""
    transformed_data = {}
    
    # Process SAQ data
    with open(saq_path, 'r', encoding='utf-8') as f:
        saq_data = json.load(f)
    
    # Transform each question into a learning unit
    for i, question in enumerate(saq_data.get('questions', [])):
        lu_id = f"LU{i+1}"
        transformed_data[lu_id] = {
            "Question": question.get('question_statement', ''),
            "Answer": question.get('answer', []) if isinstance(question.get('answer', []), list) 
                     else [question.get('answer', '')],
            "LO": question.get('scenario', ''),
            "RetrievedSources": question.get('retrieved_sources', [])
        }
    
    # Process PP data if provided
    if pp_path and os.path.exists(pp_path):
        try:
            with open(pp_path, 'r', encoding='utf-8') as f:
                pp_data = json.load(f)
            
            # Get the current count of learning units
            start_idx = len(transformed_data) + 1
            
            # Add PP questions
            for i, question in enumerate(pp_data.get('questions', [])):
                lu_id = question.get('learning_outcome_id') or f"LU{start_idx + i}"
                transformed_data[lu_id] = {
                    "Question": question.get('question_statement', ''),
                    "Answer": question.get('answer', {}).get('expected_output', ''),
                    "LO": pp_data.get('scenario', ''),
                    "RetrievedSources": question.get('retrieved_sources', [])
                }
        except Exception as e:
            print(f"Error processing PP assessment data: {e}")
    
    # Save the transformed data for debugging
    os.makedirs("output_json", exist_ok=True)
    with open("output_json/parsed_TSC.json", 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, indent=2)
    
    return transformed_data

async def run_evaluation():
    """Run evaluation on the generated RAG outputs"""
    
    # Create output directory if it doesn't exist
    output_dir = "evaluation_results"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load resources
    config, embed_model = load_shared_resources()
    
    print("Starting evaluation process...")
    
    # 1. Transform the assessment data
    print("Transforming assessment data...")
    saq_path = "output_json/saq_assessment.json"
    pp_path = "output_json/pp_assessment.json"
    
    # Check if files exist
    if not os.path.exists(saq_path):
        print(f"Warning: SAQ assessment file not found at {saq_path}")
    if not os.path.exists(pp_path):
        print(f"Warning: PP assessment file not found at {pp_path}")
    
    transformed_data = transform_assessment_data(saq_path, pp_path)
    
    # 1. Evaluate retrieval quality
    print("Evaluating retrieval quality...")
    try:
        retrieval_results = await evaluate_retrieval_quality("output_json/parsed_TSC.json")
    except Exception as e:
        print(f"Error during retrieval evaluation: {e}")
        retrieval_results = {"error": str(e)}
    
    # 2. Evaluate educational quality
    print("Evaluating educational assessment quality...")
    try:
        # Use the transformed data directly
        assessment_results = evaluate_educational_quality("output_json/parsed_TSC.json")
    except Exception as e:
        print(f"Error during assessment evaluation: {e}")
        assessment_results = {"error": str(e)}
    
    # Skip ablation study since it requires more complex setup
    
    # Combine results
    results = {
        "retrieval": retrieval_results,
        "assessment": assessment_results,
        "ablation": {}  # Skip for now
    }
    
    # Save raw results
    results_file = os.path.join(output_dir, "evaluation_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Generate visualization report
    report_file = os.path.join(output_dir, "evaluation_report.html")
    create_evaluation_report(results, report_file)
    
    print(f"Evaluation complete. Results saved to {results_file}")
    print(f"Report generated at {report_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_evaluation())