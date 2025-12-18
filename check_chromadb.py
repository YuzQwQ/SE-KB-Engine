import chromadb
from chromadb.config import Settings
import os

persist_dir = os.path.join(os.getcwd(), "se_kb", "vector_store")
client = chromadb.PersistentClient(path=persist_dir, settings=Settings(allow_reset=True))

print("Checking collections...")
collections = client.list_collections()
print(f"Found {len(collections)} collections.")

total_docs = 0
for col in collections:
    count = col.count()
    print(f"Collection: {col.name}, Documents: {count}")
    total_docs += count

print(f"Total documents: {total_docs}")
