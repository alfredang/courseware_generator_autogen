from redisvl.schema import IndexSchema

def define_custom_schema():
    """Define the Redis index schema for evaluation purposes only"""

    schema = IndexSchema.from_dict({
        "name": "rag_assessment_idx",
        "prefix": "doc:",
        "fields": [
            {"name": "text", "type": "text"},
            {"name": "embedding", "type": "vector", "attrs": {
                "dims": 384,  # For bge-small-en
                "distance_metric": "cosine",
                "algorithm": "hnsw"
            }},
            {"name": "file_path", "type": "text"},
            {"name": "file_name", "type": "text"},
            {"name": "file_type", "type": "text"},
            {"name": "file_size", "type": "numeric"},
            {"name": "creation_date", "type": "text"},
            {"name": "last_modified_date", "type": "text"}
        ]
    })

    return schema