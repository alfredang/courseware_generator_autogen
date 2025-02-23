import os
import yaml
import logging
from google.cloud import firestore
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path, override=True)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)

config = load_config()
FIRESTORE_DB_NAME = config.get("firestore_db_name", "(default)")
FIRESTORE_NAMESPACE_BASE = config.get("firestore_namespace", None) # Base namespace from config
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = config["project_id"]


def delete_firestore_collection(project_id, database_name, namespace):
    """Deletes all documents in a Firestore collection."""

    if database_name == "(default)":
        db = firestore.Client(project=project_id)
    else:
        db = firestore.Client(project=project_id, database=database_name)


    if namespace:
        collection_ref = db.collection(namespace)
    else:
        logger.error("Firestore Namespace is not configured.")
        return

    logger.info(f"Deleting all documents from Firestore collection: '{collection_ref._path}' in project '{project_id}', database '{database_name}'")

    try:
        # Get all documents in the collection
        docs = collection_ref.list_documents()
        num_deleted = 0

        # Iterate and delete each document in batches for efficiency (batch size 500 - Firestore limit)
        batch_size = 500
        doc_batch = []
        for doc in docs:
            doc_batch.append(doc)
            if len(doc_batch) >= batch_size:
                with db.transaction() as tx: # Using transaction for batch delete
                    for doc_to_delete in doc_batch:
                        tx.delete(doc_to_delete)
                num_deleted += len(doc_batch)
                doc_batch = [] # Clear batch

        # Delete any remaining documents in the last batch
        if doc_batch:
            with db.transaction() as tx:
                for doc_to_delete in doc_batch:
                    tx.delete(doc_to_delete)
            num_deleted += len(doc_batch)


        logger.info(f"Successfully deleted {num_deleted} documents from collection: '{collection_ref._path}'")

    except Exception as e:
        logger.error(f"Error deleting Firestore collection '{namespace}': {e}")



if __name__ == "__main__":
    project_id = PROJECT_ID
    database_name = FIRESTORE_DB_NAME
    namespace_base = FIRESTORE_NAMESPACE_BASE # Get base namespace

    if not namespace_base:
        logger.error("Firestore Namespace is not configured. Please set 'firestore_namespace' in config.yaml.")
    elif not project_id:
        logger.error("Project ID is not configured. Please set 'project_id' in config.yaml.")
    else:
        # Define the three collection names based on the base namespace
        collection_names_to_delete = [
            f"{namespace_base}_data",
            f"{namespace_base}_metadata",
            f"{namespace_base}_ref_doc_info"
        ]

        confirmation = input(f"Are you sure you want to delete all documents from the following Firestore collections in project '{project_id}' and database '{database_name}'?\n{collection_names_to_delete}\n(yes/no): ").lower()
        if confirmation == "yes":
            for collection_name in collection_names_to_delete:
                logger.info(f"\n--- Deleting collection: {collection_name} ---")
                delete_firestore_collection(project_id, database_name, collection_name) # Call delete for each collection
            logger.info("\n--- Deletion process completed for all collections. ---")
        else:
            logger.info("Deletion cancelled by user.")