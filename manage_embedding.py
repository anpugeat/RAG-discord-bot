from llama_index import SimpleDirectoryReader, VectorStoreIndex, load_index_from_storage
from llama_index.storage.storage_context import StorageContext
from dotenv import load_dotenv
import logging
import sys

# Load environment variables from the .env file
load_dotenv()

# Logging level set to INFO
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))


async def load_index(directory_path: str = r'data'):
    """
    Main function to initialize the knowledge base.
    1. Reads files from the 'data' folder.
    2. Checks if a processed index already exists in 'storage'.
    3. If yes, loads it (fast). If no, creates a new one (slower, costs API credits).
    """
    
    # Read all docs (PDFs, text files) from directory
    documents = SimpleDirectoryReader(directory_path, filename_as_id=True).load_data()
    print(f"loaded documents with {len(documents)} pages")

    try:
        # Try to find an existing index on the disk (in the ./storage folder)
        storage_context = StorageContext.from_defaults(persist_dir="./storage")
        
        # Load the index (this avoids re-sending data to OpenAI if it was already done)
        index = load_index_from_storage(storage_context)
        logging.info("Index loaded from storage.")
        
    except FileNotFoundError:
        # If storage directory/files don't exist, build a new index 
        logging.info("Index not found. Creating a new one...")
        
        # Vectorise our raw documents
        index = VectorStoreIndex.from_documents(documents)
        
        # Save our new index to the hard drive for future use
        index.storage_context.persist()
        logging.info("New index created and persisted to storage.")

    return index


async def update_index(directory_path: str = r'data'):
    """
    Smart update function triggered by /updatedb.
    It compares the current files in 'data' vs the saved index.
    It ONLY updates files that are new or changed, saving time and money.
    """
    try:
        # Read the current files in the directory
        documents = SimpleDirectoryReader(directory_path, filename_as_id=True).load_data()
    except FileNotFoundError:
        # Case where dir is invalid
        logging.error("Invalid document directory path.")
        return None

    try:
        # Load the existing index so we can compare against it
        storage_context = StorageContext.from_defaults(persist_dir="./storage")
        index = load_index_from_storage(storage_context)
        logging.info("Existing index loaded from storage.")

        # Refresh the index
        refreshed_docs = index.refresh_ref_docs(
            documents, 
            update_kwargs={"delete_kwargs": {"delete_from_docstore": True}}
        )

        # Print updated doc results
        print(refreshed_docs)
        print('Number of newly inserted/refreshed docs: ', sum(refreshed_docs))

        # Save the updated index back to disk
        index.storage_context.persist()
        logging.info("Index refreshed and persisted to storage.")
        
        return refreshed_docs

    except FileNotFoundError:
        # Case where an index is updated before it exists
        logging.error("Index is not created yet. Please run a query first to generate the initial index.")
        return None