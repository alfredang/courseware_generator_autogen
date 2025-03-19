import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime

from retrieval_metrics import evaluate_retrieval_quality
from assessment_metrics import evaluate_educational_quality
from ablation_study import run_ablation_study
from visualization import create_evaluation_report

async def run_full_evaluation(output_dir="evaluation_results"):
    """Run all evaluation metrics and save results."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {}
    
    # 1. Evaluate retrieval quality
    print("Evaluating retrieval quality...")
    retrieval_results = await evaluate_retrieval_quality()
    results["retrieval"] = retrieval_results
    
    # 2. Evaluate educational quality
    print("Evaluating educational assessment quality...")
    assessment_results = evaluate_educational_quality()
    results["assessment"] = assessment_results
    
    # 3. Run ablation study
    print("Running ablation study...")
    ablation_results = await run_ablation_study()
    results["ablation"] = ablation_results
    
    # Save raw results
    results_file = os.path.join(output_dir, f"evaluation_results_{timestamp}.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Generate visualization report
    report_file = os.path.join(output_dir, f"evaluation_report_{timestamp}.html")
    create_evaluation_report(results, report_file)
    
    print(f"Evaluation complete. Results saved to {results_file}")
    print(f"Report generated at {report_file}")
    
    return results

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_full_evaluation())