# query_chain.py
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.redis import RedisVectorStore
from redisvl.schema import IndexSchema # Import for schema definition (if needed to re-establish vector store)
from config_loader import load_shared_resources # Import shared resources loader
import logging

from llama_index.core.query_pipeline import (
    QueryPipeline,
    InputComponent,
    ArgPackComponent,
)


def define_custom_schema(): # Re-define schema to connect to existing Redis vector store. Must match indexing schema.
    """Defines the custom Redis index schema - MUST MATCH indexing schema."""
    return IndexSchema.from_dict(
        {
            "index": {"name": "redis_vector_store", "prefix": "doc"},
            "fields": [
                {"type": "tag", "name": "id"},
                {"type": "tag", "name": "doc_id"},
                {"type": "text", "name": "text"},
                {"type": "numeric", "name": "updated_at"},
                {"type": "tag", "name": "file_name"},
                {
                    "type": "vector",
                    "name": "vector",
                    "attrs": {
                        "dims": 384, # MUST match indexing schema
                        "algorithm": "hnsw",
                        "distance_metric": "cosine",
                    },
                },
            ],
        }
    )


def create_query_engine(embed_model):
    """Creates and returns the query engine."""
    custom_schema = define_custom_schema() # Re-define the schema to connect
    vector_store = RedisVectorStore( # Re-instantiate RedisVectorStore to connect to existing index.
        schema=custom_schema,
        redis_url="redis://localhost:6379",
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store, embed_model=embed_model
    )
    return index.as_query_engine(similarity_top_k=10) # or configure as needed


def run_query(query_text):
    """Runs a query against the index and prints the response."""
    config, embed_model = load_shared_resources() # Load shared resources
    llm = Gemini(api_key=config.get("gemini_api_key") or config.get("GEMINI_API_KEY") or config.get("GEMINI_API"), model_name=config.get("llm_model")) # Re-initialize Gemini LLM - ensure API key is loaded (adjust keys if needed)
    query_engine = create_query_engine(embed_model)
    response = query_engine.query(query_text)
    print(f"Query: {query_text}")
    print(f"Response: {response}")
    logging.info(f"Query: {query_text} - Response received (from query_chain.py).")
    return response # return response if you want to use it programmatically

if __name__ == "__main__":
    query_text = "What is the document about?" # Example query, you can modify or take input
    run_query(query_text)
    logging.info("Query process completed (from query_chain.py).")