import os
import json
import tempfile
from typing import Dict, Any
import asyncio

# Import your workflow components
from ..retrieval_workflow import PydanticWorkflow, LearningUnitDetails, LearningUnits
from ..config_loader import load_shared_resources

# Modified retrieval function for ablation testing
async def create_modified_workflow(
    use_reranker: bool = True,
    filter_toc: bool = True,
    enhanced_query: bool = True,
    top_k: int = 5
) -> PydanticWorkflow:
    """Create a modified workflow with specific features enabled/disabled."""
    # Base workflow with everything disabled
    workflow = PydanticWorkflow()
    
    # Override the retrieve method based on configuration
    async def modified_retrieve(self, ctx, ev):
        """Modified retrieve step with configurable components."""
        query = ev.query
        lu_details = ev.lu_details
        index = ev.index
        
        if not query or index is None:
            return None
            
        # Construct query based on configuration
        if enhanced_query and lu_details:
            query_str = f"""
            Learning Objective: {lu_details.LO}
            Knowledge Points: {', '.join(list(lu_details.Knowledge.root.values()))}
            I need learning content that focuses on these topics.
            """
        else:
            # Simple keyword query
            query_str = query
            
        # Basic retrieval
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query_str)
        
        # Apply reranker if enabled
        if use_reranker:
            from llama_index.core.postprocessor import SentenceTransformerRerank
            reranker = SentenceTransformerRerank(
                model="cross-encoder/ms-marco-MiniLM-L-12-v2",
                top_n=min(5, len(nodes))
            )
            nodes = reranker.postprocess_nodes(nodes, query_str=query_str)
        
        # Filter TOC nodes if enabled
        if filter_toc:
            filtered_nodes = []
            for node in nodes:
                content = node.node.get_content(metadata_mode=MetadataMode.NONE)
                is_toc = any([
                    "table of contents" in content.lower(),
                    "contents" in content.lower() and len(content.split()) < 100,
                    content.count("\n") > content.count(".") * 2,
                    content.count("...") > 3
                ])
                if not is_toc:
                    filtered_nodes.append(node)
            nodes = filtered_nodes if filtered_nodes else nodes  # Fall back to original if all filtered
        
        # Save sources
        if lu_details:
            lu_details.RetrievedSources = [
                {
                    "text": node.node.get_content(metadata_mode=MetadataMode.NONE),
                    "score": str(node.score),
                    "metadata": str(node.node.metadata) if hasattr(node.node, "metadata") else ""
                } 
                for node in nodes
            ]
            await ctx.set("lu_details", lu_details)
            
        return RetrieverEvent(nodes=nodes)
    
    # Replace the retrieve method
    workflow.retrieve = modified_retrieve.__get__(workflow)
    
    return workflow

async def evaluate_single_config(config: Dict[str, Any], test_units: Dict[str, Any]):
    """Run evaluation for a single configuration."""
    # Create the modified workflow
    workflow = await create_modified_workflow(
        use_reranker=config["use_reranker"],
        filter_toc=config["filter_toc"],
        enhanced_query=config["enhanced_query"]
    )
    
    results = {
        "config": config,
        "unit_results": {}
    }
    
    # Load resources
    config_dict, embed_model = load_shared_resources()
    
    # Run on each test unit 
    for lu_name, lu_data in test_units.items():
        # Create learning unit object
        lu = LearningUnitDetails.model_validate(lu_data)
        
        # Run workflow
        ctx = Context()
        ev = LUDataEvent(
            query=lu.LO,
            lu_details=lu,
            index=your_index  # You need to access your index here
        )
        
        # Execute workflow
        result_ev = await workflow.run(ctx, ev)
        
        # Evaluate results
        if hasattr(lu, "RetrievedSources") and lu.RetrievedSources:
            sources = lu.RetrievedSources
            metrics = {
                "source_count": len(sources),
                "avg_source_length": sum(len(s["text"]) for s in sources) / max(len(sources), 1),
                # Add evaluation metrics here
            }
            
            results["unit_results"][lu_name] = metrics
    
    # Calculate aggregated metrics
    if results["unit_results"]:
        results["avg_source_count"] = sum(r["source_count"] for r in results["unit_results"].values()) / len(results["unit_results"])
        # Add more aggregated metrics as needed
    
    return results

async def run_ablation_study(data_path="output_json/parsed_TSC.json"):
    """Run ablation study with different component combinations."""
    # Load data
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    # Select a subset of units for testing
    test_units = {}
    for i, (lu_name, lu_data) in enumerate(data.items()):
        if i >= 5:  # Limit to 5 units for faster testing
            break
        test_units[lu_name] = lu_data
    
    # Define configurations to test
    ablation_configs = [
        {"name": "full_system", "use_reranker": True, "filter_toc": True, "enhanced_query": True},
        {"name": "no_reranker", "use_reranker": False, "filter_toc": True, "enhanced_query": True},
        {"name": "no_toc_filter", "use_reranker": True, "filter_toc": False, "enhanced_query": True},
        {"name": "no_enhanced_query", "use_reranker": True, "filter_toc": True, "enhanced_query": False},
        {"name": "baseline", "use_reranker": False, "filter_toc": False, "enhanced_query": False}
    ]
    
    # Run evaluation for each configuration
    results = {}
    for config in ablation_configs:
        print(f"Testing configuration: {config['name']}")
        config_results = await evaluate_single_config(config, test_units)
        results[config["name"]] = config_results
    
    return results