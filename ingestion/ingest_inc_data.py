import json
import os
import sys
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path to import config
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import CHROMA_DB_PATH, RCA_DATA_INGEST_PATH

# Load environment variables
load_dotenv()

# Get OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Load JSON file using config path
with open(RCA_DATA_INGEST_PATH, "r") as f:
    data = json.load(f)

# Create OpenAI embedding function
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"  # or "text-embedding-3-large" for better quality
)

# Create persistent Chroma client using config path
client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

# Create/Get collection with OpenAI embeddings
collection = client.get_or_create_collection(
    name="rca_knowledge_base",
    embedding_function=openai_ef  # type: ignore
)

# Prepare data
ids = []
documents = []
metadatas = []

for item in data:
    ids.append(item["id"])
    documents.append(item["document"])
    
    # Convert metadata to ChromaDB-compatible format
    # ChromaDB doesn't support lists in metadata, so convert components to comma-separated string
    metadata = {
        "components": ", ".join(item["metadata"]["components"]),
        "date_occurred": item["metadata"]["date_occurred"],
        "cbc": item["metadata"]["cbc"] if item["metadata"]["cbc"] else ""
    }
    metadatas.append(metadata)

# Ingest
collection.add(
    ids=ids,
    documents=documents,
    metadatas=metadatas
)

print(f"Ingested {len(ids)} RCA records into ChromaDB using OpenAI embeddings")
print(f"Collection: {collection.name}")
print(f"Total documents: {collection.count()}")