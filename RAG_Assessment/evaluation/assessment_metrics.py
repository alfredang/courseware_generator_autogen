import os
import json
import pandas as pd
import re
from collections import Counter
from typing import List, Dict, Any

# Bloom's taxonomy keywords by level
BLOOMS_KEYWORDS = {
    "remember": [
        "define", "describe", "identify", "know", "label", "list", "match", "name", 
        "outline", "recall", "recognize", "state", "select", "memorize"
    ],
    "understand": [
        "comprehend", "convert", "defend", "distinguish", "estimate", "explain", 
        "extend", "generalize", "give example", "infer", "interpret", "paraphrase", 
        "predict", "summarize", "translate"
    ],
    "apply": [
        "apply", "change", "compute", "demonstrate", "discover", "manipulate", 
        "modify", "operate", "predict", "prepare", "produce", "relate", "show", 
        "solve", "use", "calculate"
    ],
    "analyze": [
        "analyze", "break down", "compare", "contrast", "diagram", "deconstruct", 
        "differentiate", "discriminate", "distinguish", "examine", "outline", 
        "separate", "categorize", "appraise", "test"
    ],
    "evaluate": [
        "appraise", "argue", "assess", "choose", "compare", "defend", "estimate", 
        "judge", "predict", "rate", "evaluate", "select", "support", "value", "critique", 
        "score", "review"
    ],
    "create": [
        "arrange", "assemble", "collect", "compose", "construct", "create", "design", 
        "develop", "formulate", "manage", "organize", "plan", "prepare", "propose", 
        "setup", "devise", "generate", "build"
    ]
}

def classify_bloom_level(question_text: str) -> str:
    """Classify a question according to Bloom's taxonomy level."""
    question_lower = question_text.lower()
    
    # Check for each level, starting with highest
    for level in ["create", "evaluate", "analyze", "apply", "understand", "remember"]:
        for keyword in BLOOMS_KEYWORDS[level]:
            if keyword in question_lower:
                return level
    
    # Default to remember if no keywords match
    return "remember"

def classify_question_type(question_text: str) -> str:
    """Classify the type of question (multiple choice, short answer, etc.)."""
    question_lower = question_text.lower()
    
    if re.search(r'\b[a-d][\.|\)]\s', question_text) or "choose" in question_lower or "select" in question_lower:
        return "multiple_choice"
    elif "scenario" in question_lower or "case" in question_lower or len(question_text) > 300:
        return "scenario"
    else:
        return "short_answer"

def evaluate_educational_quality(data_path="output_json/parsed_TSC.json"):
    """Evaluate quality of assessment questions from an educational perspective."""
    # Load data
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    results = {
        "bloom_taxonomy": {level: 0 for level in BLOOMS_KEYWORDS.keys()},
        "question_types": {"multiple_choice": 0, "short_answer": 0, "scenario": 0},
        "alignment_scores": [],
        "question_length": [],
        "questions_per_unit": []
    }
    
    # Process each learning unit
    lu_results = {}
    for lu_name, lu_data in data.items():
        if not isinstance(lu_data, dict):
            continue
            
        questions = []
        if "Question" in lu_data and lu_data["Question"]:
            if isinstance(lu_data["Question"], str):
                questions.append(lu_data["Question"])
            elif isinstance(lu_data["Question"], list):
                questions.extend([q for q in lu_data["Question"] if isinstance(q, str)])
        
        if not questions:
            continue
            
        # Count questions per unit
        results["questions_per_unit"].append(len(questions))
        
        # Analyze questions
        unit_results = {
            "bloom_levels": Counter(),
            "question_types": Counter(),
            "question_details": []
        }
        
        for q in questions:
            # Classify question
            bloom_level = classify_bloom_level(q)
            q_type = classify_question_type(q)
            
            # Add to counters
            results["bloom_taxonomy"][bloom_level] += 1
            results["question_types"][q_type] += 1
            unit_results["bloom_levels"][bloom_level] += 1
            unit_results["question_types"][q_type] += 1
            
            # Add question length
            results["question_length"].append(len(q))
            
            # Calculate alignment score
            # (how well does the question match the learning objective)
            alignment_score = 0.0  # placeholder for actual alignment calculation
            results["alignment_scores"].append(alignment_score)
            
            # Store individual question analysis
            unit_results["question_details"].append({
                "question_text": q[:100] + "..." if len(q) > 100 else q,
                "bloom_level": bloom_level,
                "question_type": q_type,
                "length": len(q)
            })
        
        lu_results[lu_name] = unit_results
    
    # Create summary statistics
    summary = {
        "total_questions": sum(results["questions_per_unit"]),
        "total_learning_units_with_questions": len(lu_results),
        "avg_questions_per_unit": sum(results["questions_per_unit"]) / max(len(results["questions_per_unit"]), 1),
        "avg_question_length": sum(results["question_length"]) / max(len(results["question_length"]), 1),
        "bloom_distribution": {k: v / max(sum(results["bloom_taxonomy"].values()), 1) 
                              for k, v in results["bloom_taxonomy"].items()},
        "question_type_distribution": {k: v / max(sum(results["question_types"].values()), 1) 
                                      for k, v in results["question_types"].items()}
    }
    
    return {
        "summary": summary,
        "learning_units": lu_results
    }