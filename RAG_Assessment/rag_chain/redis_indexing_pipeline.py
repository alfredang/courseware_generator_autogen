# indexing_chain.py
import os
from llama_index.core import SimpleDirectoryReader
from llama_index.core.ingestion import (
    DocstoreStrategy,
    IngestionPipeline,
    IngestionCache,
)
from llama_index.storage.kvstore.redis import RedisKVStore as RedisCache
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.redis import RedisVectorStore
from redisvl.schema import IndexSchema
from config_loader import load_shared_resources  # Import shared resources loader
import logging


def create_ingestion_pipeline(embed_model, custom_schema):
    """Creates and returns the ingestion pipeline."""
    return IngestionPipeline(
        transformations=[
            SentenceSplitter(),
            embed_model,
        ],
        docstore=RedisDocumentStore.from_host_and_port(
            "localhost", 6379, namespace="document_store"
        ),
        vector_store=RedisVectorStore(
            schema=custom_schema,
            redis_url="redis://localhost:6379",
        ),
        cache=IngestionCache(
            cache=RedisCache.from_host_and_port("localhost", 6379),
            collection="redis_cache",
        ),
        docstore_strategy=DocstoreStrategy.UPSERTS,
    )


def load_documents(data_dir="./data"):
    """Loads documents from the specified directory with deterministic IDs."""
    logging.info("Loading documents...")
    documents = SimpleDirectoryReader(
        data_dir, filename_as_id=True
    ).load_data()
    logging.info(f"Documents loaded: {len(documents)}")
    if documents:
        logging.info(f"First document loaded: {documents[0]}")
    else:
        logging.warning("No documents loaded from directory!")
    return documents

def define_custom_schema():
    """Defines the custom Redis index schema."""
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
                        "dims": 384, # dims now hardcoded in schema - consider making configurable if needed
                        "algorithm": "hnsw",
                        "distance_metric": "cosine",
                    },
                },
            ],
        }
    )

def run_indexing():
    """Runs the indexing pipeline."""
    config, embed_model = load_shared_resources() # Load shared resources
    documents = load_documents()
    if not documents:
        logging.warning("No documents to index. Exiting indexing process.")
        return

    custom_schema = define_custom_schema()
    pipeline = create_ingestion_pipeline(embed_model, custom_schema)

    nodes = pipeline.run(documents=documents)
    logging.info(f"Ingested {len(nodes)} Nodes")
    print(f"Ingested {len(nodes)} Nodes") # Keep print for direct script execution feedback


if __name__ == "__main__":
    run_indexing()
    logging.info("Indexing process completed (from indexing_chain.py).")