import os
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

import sys
sys.path.append("C:/Users/marcu/AppData/Roaming/Python/Python312/site-packages")

# For RAGAS integration (if installed)
try:
    import torch
    from ragas.metrics import faithfulness, context_relevancy, context_recall, answer_relevancy
    from ragas.metrics.critique import AspectCritique
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    print("RAGAS not available. Install with: pip install ragas langchain torch transformers datasets")

# Load embeddings model for similarity calculations
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model for evaluation

async def evaluate_with_ragas(data):
    """Evaluate retrieval and answer quality using RAGAS metrics."""
    if not RAGAS_AVAILABLE:
        return {"error": "RAGAS not available. Install with: pip install ragas langchain torch datasets"}
        
    try:
        # Prepare data in the format RAGAS expects
        questions = []
        contexts = []
        answers = []
        
        for lu_name, lu_data in data.items():
            if not isinstance(lu_data, dict) or 'RetrievedSources' not in lu_data:
                continue
                
            question = lu_data.get('Question', '')
            if not question or not isinstance(question, str):
                continue
                
            sources = lu_data.get('RetrievedSources', [])
            if not sources:
                continue
                
            answer = lu_data.get('Answer', '')
            if isinstance(answer, list):
                answer = ' '.join([str(a) for a in answer])
            if not answer:
                continue
                
            # Extract text from sources
            source_texts = [s.get('text', '') for s in sources if s.get('text')]
            if not source_texts:
                continue
                
            # Add to lists
            questions.append(question)
            contexts.append(source_texts)
            answers.append(answer)
        
        if not questions:
            return {"error": "No valid question-answer pairs found for RAGAS evaluation"}
        
        # Create datasets
        import pandas as pd
        from datasets import Dataset
        
        eval_dataset = Dataset.from_pandas(pd.DataFrame({
            "question": questions,
            "contexts": contexts,
            "answer": answers
        }))
        
        # Run evaluation with RAGAS
        from ragas import evaluate
        
        print(f"Evaluating {len(questions)} question-answer pairs with RAGAS...")
        results = evaluate(
            eval_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_relevancy,
                context_recall
            ]
        )
        
        # Convert to dictionary
        metrics_results = {}
        for metric_name, score in results.items():
            metrics_results[metric_name] = float(score)
        
        return {
            "metrics": metrics_results,
            "samples_evaluated": len(questions),
            "details": [
                {
                    "question": q[:100] + "..." if len(q) > 100 else q,
                    "answer_length": len(a),
                    "num_contexts": len(c)
                } for q, a, c in zip(questions, answers, contexts)
            ]
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"RAGAS evaluation failed: {str(e)}"}

def compute_info_density(text: str) -> float:
    """Calculate information density based on text features."""
    if not text or len(text) < 10:
        return 0.0
        
    # Count features indicating information density
    sentences = len([s for s in text.split('.') if len(s.strip()) > 0])
    avg_words_per_sentence = len(text.split()) / max(sentences, 1)
    keyword_ratio = sum(1 for word in text.lower().split() 
                      if len(word) > 5 and word not in common_stopwords) / max(len(text.split()), 1)
    
    # TOC and navigation patterns reduce score
    has_toc_patterns = any([
        "contents" in text.lower() and len(text) < 500,
        text.count("...") > 2,
        text.count("\n") > sentences * 1.5
    ])
    
    base_score = (0.4 * min(avg_words_per_sentence / 15, 1.0) + 
                  0.6 * keyword_ratio)
    
    # Penalize TOC patterns
    if has_toc_patterns:
        base_score *= 0.3
        
    return base_score

def evaluate_document_relevance(query: str, docs: List[str]) -> List[float]:
    """Measure relevance between query and retrieved documents using embeddings."""
    query_embedding = embedding_model.encode([query], convert_to_tensor=True)
    doc_embeddings = embedding_model.encode(docs, convert_to_tensor=True)
    
    # Calculate cosine similarity
    similarities = cosine_similarity(
        query_embedding.cpu().numpy(), 
        doc_embeddings.cpu().numpy()
    )[0]
    
    return similarities.tolist()

async def evaluate_retrieval_quality(data_path="output_json/parsed_TSC.json"):
    """Evaluate quality of retrieved passages for learning units."""
    # Load data
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    # Metrics to calculate
    metrics = {
        "relevance_scores": [],
        "info_density_scores": [],
        "relevance_to_knowledge": [],
        "source_counts": [],
        "avg_source_length": []
    }
    
    all_results = {}
    
    # Process each learning unit
    for lu_name, lu_data in data.items():
        if not isinstance(lu_data, dict) or 'RetrievedSources' not in lu_data:
            continue
            
        sources = lu_data.get('RetrievedSources', [])
        if not sources:
            continue
            
        source_texts = [s.get('text', '') for s in sources if s.get('text')]
        if not source_texts:
            continue
            
        # Create evaluation query based on learning unit data
        eval_query = f"Learning Objective: {lu_data.get('LO', '')}"
        if 'Knowledge' in lu_data and isinstance(lu_data['Knowledge'], dict):
            knowledge_values = [v for v in lu_data['Knowledge'].values() 
                              if isinstance(v, str) and v]
            if knowledge_values:
                eval_query += f" Knowledge: {'. '.join(knowledge_values)}"
        
        # Calculate metrics
        relevance_scores = evaluate_document_relevance(eval_query, source_texts)
        info_density = [compute_info_density(text) for text in source_texts]
        
        # Store metrics for this learning unit
        lu_result = {
            "lu_name": lu_name,
            "sources_count": len(sources),
            "avg_relevance": np.mean(relevance_scores) if relevance_scores else 0,
            "avg_info_density": np.mean(info_density) if info_density else 0,
            "avg_source_length": np.mean([len(t) for t in source_texts]) if source_texts else 0,
            "source_details": [
                {
                    "relevance": score,
                    "info_density": density,
                    "length": len(text),
                    "text_preview": text[:100] + "..." if len(text) > 100 else text
                }
                for text, score, density in zip(source_texts, relevance_scores, info_density)
            ]
        }
        
        # Add to overall metrics
        metrics["relevance_scores"].extend(relevance_scores)
        metrics["info_density_scores"].extend(info_density)
        metrics["source_counts"].append(len(sources))
        metrics["avg_source_length"].append(np.mean([len(t) for t in source_texts]))
        
        # Store individual LU results
        all_results[lu_name] = lu_result
    
    # Calculate aggregate metrics
    summary = {
        "avg_relevance": np.mean(metrics["relevance_scores"]) if metrics["relevance_scores"] else 0,
        "avg_info_density": np.mean(metrics["info_density_scores"]) if metrics["info_density_scores"] else 0,
        "avg_source_count": np.mean(metrics["source_counts"]) if metrics["source_counts"] else 0,
        "avg_source_length": np.mean(metrics["avg_source_length"]) if metrics["avg_source_length"] else 0,
        "total_learning_units_evaluated": len(all_results)
    }

    ragas_results = {}
    if RAGAS_AVAILABLE:
        try:
            print("Running RAGAS evaluation...")
            ragas_results = await evaluate_with_ragas(data)
        except Exception as e:
            print(f"Error during RAGAS evaluation: {e}")
            ragas_results = {"error": str(e)}
    else:
        ragas_results = {"error": "RAGAS not available"}
    
    
    return {
        "summary": summary,
        "learning_units": all_results,
        "ragas": ragas_results
    }

# Common stopwords for info density calculation
common_stopwords = {
    "the", "and", "of", "to", "a", "in", "for", "is", "on", "that", "by", "this", "with", 
    "you", "it", "not", "or", "be", "are", "from", "at", "as", "your", "have", "more", "an", "was"
}