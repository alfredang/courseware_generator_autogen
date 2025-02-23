import os
import yaml
from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.extractors import QuestionsAnsweredExtractor
from llama_index.core.node_parser import (
    HierarchicalNodeParser,
    SentenceSplitter,
)
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.schema import (
    NodeRelationship,
    RelatedNodeInfo,
    TextNode,
)
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.storage.docstore.firestore import FirestoreDocumentStore
from pydantic import BaseModel
import chromadb
from tqdm.asyncio import tqdm_asyncio
import asyncio
import logging
from typing import List
from llama_index.core.prompts import PromptTemplate
from llama_index.readers.file import PDFReader
from dotenv import load_dotenv
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path, override=True)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)

config = load_config()
CHUNK_SIZES = config["chunk_sizes"]
CHUNK_SIZE = config.get("chunk_size", 512)
CHUNK_OVERLAP = config.get("chunk_overlap", 50)
INDEXING_METHOD = config["indexing_method"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FIRESTORE_DB_NAME = config.get("firestore_db_name", "(default)")
FIRESTORE_NAMESPACE = config.get("firestore_namespace", None)
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
EMBEDDING_MODEL = config.get("embedding_model")
LLM_MODEL = config.get("llm_model")

QA_EXTRACTION_PROMPT = PromptTemplate(
    template="""\
Here is the context:
---------------------
{context_str}
---------------------
Given the contextual information, generate 1 questions this document can answer.\
"""
)

QA_PARSER_PROMPT = PromptTemplate(
    template="""\
Here is a list of questions:
---------------------
{questions_list}
---------------------
Format this into a JSON that can be parsed by pydantic, and answer with the format:
{
    "questions_list": [list of questions]
}
"""
)

class QuesionsAnswered(BaseModel):
    """List of Questions Answered by Document"""
    questions_list: List[str]

def generate_doc_id(document: Document) -> str:
    """Generates a unique ID for a document based on content, filename, and page_label."""
    combined_content = (
        document.text
        + document.metadata.get("filename", "")
        + document.metadata.get("page_label", "") # ADD PAGE_LABEL
    )
    return hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

async def create_qa_index(li_docs, docstore, embed_model, llm):
    """Creates an index of hypothetical questions."""

    qa_extractor = QuestionsAnsweredExtractor(
        llm=llm, questions=1, prompt_template=QA_EXTRACTION_PROMPT.template
    )

    async def extract_batch(li_docs):
        return await tqdm_asyncio.gather(
            *[qa_extractor.aextract(doc) for doc in li_docs]
        )

    metadata_results = await extract_batch(li_docs)
    # metadata_list is a list of lists of MetadataExtractionResult objects.
    # Flatten and extract metadata
    metadata_list = [res for sublist in metadata_results for res in sublist] # Keep the dictionaries

    program = LLMTextCompletionProgram.from_defaults(
        output_cls=QuesionsAnswered,
        prompt_template_str=QA_PARSER_PROMPT.template,  # Use .template
        llm=llm,
        verbose=True,
    )

    async def parse_batch(metadata_list):
        return await asyncio.gather(
            *[program.acall(questions_list=meta.get("questions_list", []))
              for meta in metadata_list],
            return_exceptions=True,
        )
    parsed_questions = await parse_batch(metadata_list)

    q_docs = []
    for doc, questions in zip(li_docs, parsed_questions):
        if isinstance(questions, Exception):
            logger.info(f"Unparsable questions exception {questions}")
            continue
        if isinstance(questions, QuesionsAnswered) and questions.questions_list:
            for q in questions.questions_list:
                logger.info(f"Question extracted: {q}")
                q_doc = Document(text=q)
                q_doc.doc_id = generate_doc_id(q_doc)
                q_doc.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                    node_id=doc.doc_id  # Use original doc's ID
                )
                q_docs.append(q_doc)

    for q_doc in q_docs:
        existing_doc = docstore.get_document(q_doc.doc_id)
        if existing_doc:
            logger.info(f"Skipping question document with ID {q_doc.doc_id} (already exists).")
            continue
        docstore.add_documents([q_doc])

    chroma_client = chromadb.PersistentClient(path="./chroma_db_qa")
    chroma_collection = chroma_client.get_or_create_collection("qa_collection")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )
    VectorStoreIndex(
        nodes=q_docs,
        storage_context=storage_context,
        embed_model=embed_model,
        llm=llm,
    )

def create_hierarchical_index(li_docs, docstore, vector_store, embed_model, llm):
    """Creates a hierarchical index."""

    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=CHUNK_SIZES)
    nodes = node_parser.get_nodes_from_documents(li_docs)

    leaf_nodes = [node for node in nodes if NodeRelationship.CHILD not in node.relationships]
    num_leaf_nodes = len(leaf_nodes)
    num_nodes = len(nodes)
    logger.info(f"There are {num_leaf_nodes} leaf_nodes and {num_nodes} total nodes")

    for node in nodes:
        node.node_id = generate_doc_id(node) # Changed to node.node_id
        existing_doc = docstore.get_document(node.node_id) # Changed to node.node_id
        if existing_doc:
            logger.info(f"Skipping node with ID {node.node_id} (already exists).") # Changed to node.node_id
            continue
        docstore.add_documents([node])

    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )
    VectorStoreIndex(
        nodes=leaf_nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        llm=llm,
    )

def create_flat_index(li_docs, docstore, vector_store, embed_model, llm):
    """Creates a flat index."""
    sentence_splitter = SentenceSplitter(chunk_size=CHUNK_OVERLAP)
    node_chunk_list = []
    for doc in li_docs:
        # Simplified: Directly use doc.text and doc.metadata
        chunks = sentence_splitter.split_text(doc.text)

        for chunk_text in chunks:
            node = TextNode(text=chunk_text)
            node.doc_id = generate_doc_id(node)
            node.metadata["filename"] = doc.metadata.get("filename", "") #Keep Metadata
            node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                node_id=doc.doc_id  # Use original doc's ID
            )
            node_chunk_list.append(node)

    logger.info("embedding...")

    for node in node_chunk_list:
        existing_doc = docstore.get_document(node.doc_id)
        if existing_doc:
            logger.info(f"Skipping node with ID {node.doc_id} (already exists).")
            continue
        docstore.add_documents([node])

    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )

    VectorStoreIndex(
        nodes=node_chunk_list,  # Use the correctly populated node list
        storage_context=storage_context,
        embed_model=embed_model,
        llm=llm,
    )

def load_docs_from_directory(directory_path: str) -> List[Document]:
    """Loads documents from a directory, handling PDFs and TXTs, and sets doc_id."""
    documents = []
    loader = PDFReader()

    for filename in os.listdir(directory_path):
        if filename.startswith("."):
            continue
        filepath = os.path.join(directory_path, filename)
        try:
            if filename.lower().endswith(".pdf"):
                docs = loader.load_data(file=filepath)
                logger.info(f"PDFReader loaded {len(docs)} documents from {filename}")
                for i, doc in enumerate(docs): # Enumerate to potentially use index if needed
                    doc.metadata["filename"] = filename
                    # Log the metadata to inspect what's available
                    logger.info(f"Document metadata before ID generation: {doc.metadata}") # ADDED METADATA LOGGING
                    doc.doc_id = generate_doc_id(doc)
                    logger.info(f"Loaded document ID (from load_docs): {doc.doc_id}, filename: {filename}")
                    documents.append(doc)
            elif filename.lower().endswith(".txt"):
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
                    doc = Document(text=text, metadata={"filename": filename})
                    logger.info(f"Document metadata before ID generation (TXT): {doc.metadata}") # ADDED METADATA LOGGING for TXT too, just for consistency
                    doc.doc_id = generate_doc_id(doc)
                    logger.info(f"Loaded document ID (from load_docs): {doc.doc_id}, filename: {filename}")
                    documents.append(doc)
            else:
                logger.warning(f"Skipping unsupported file type: {filename}")

        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")

    return documents

def main():
    """Main function to run the indexing pipeline and query the index."""
    documents = load_docs_from_directory("./data")
    if not documents:
        logger.error("No documents loaded. Exiting.")
        return

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    embed_model = GeminiEmbedding(
        model_name=EMBEDDING_MODEL, api_key=GEMINI_API_KEY
    )
    llm = Gemini(api_key=GEMINI_API_KEY, model_name=LLM_MODEL, temperature=0.0)

    Settings.llm = llm
    Settings.embed_model = embed_model

    chroma_client = chromadb.PersistentClient(path="./chroma_db_main")
    chroma_collection = chroma_client.get_or_create_collection("main_collection")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    docstore = FirestoreDocumentStore.from_database(
        project=config["project_id"], database=FIRESTORE_DB_NAME, namespace=FIRESTORE_NAMESPACE
    )

    # --- Index Creation (Conditional) ---
    if config.get("create_qa_index_flag", False): # RE-ENABLED
        asyncio.run(create_qa_index(documents, docstore, embed_model, llm))

    # Add the *original* documents (after setting their IDs) OUTSIDE QA
    for doc in documents:
        logger.info(f"Checking doc_id before get_document: {doc.doc_id}") # ADDED LOG
        existing_doc = docstore.get_document(doc.doc_id) # RE-ENABLED
        if existing_doc: # RE-ENABLED
            logger.info(f"Skipping original document with ID {doc.doc_id} (already exists).")
            continue
        docstore.add_documents([doc])

    if config.get("create_vector_index_flag", True): # RE-ENABLED
        if INDEXING_METHOD == "hierarchical":
            create_hierarchical_index(documents, docstore, vector_store, embed_model, llm)
        elif INDEXING_METHOD == "flat":
            create_flat_index(documents, docstore, vector_store, embed_model, llm)
        else:
            logger.error(f"Invalid indexing method: {INDEXING_METHOD}")

    # --- Load Index from Storage --- # RE-ENABLED
    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

    # --- Query Engine --- # RE-ENABLED
    query_engine = index.as_query_engine(similarity_top_k=5)

    # --- Interactive Query Loop --- # RE-ENABLED
    while True:
        try:
            query_text = input("Enter your query (or type 'exit' to quit): ")
            if query_text.lower() == "exit":
                break

            response = query_engine.query(query_text)
            print("\nResponse:\n", response)

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Error during query: {e}")

if __name__ == "__main__":
    main()