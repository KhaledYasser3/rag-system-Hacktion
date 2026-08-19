import os
import sys
import shutil

# Configure python path to find the package src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rag_system.config.config import QDRANT_LOCAL_PATH, QDRANT_COLLECTION
from qdrant_client import QdrantClient

def reset_db():
    print("=" * 60)
    print("  RESETTING VECTOR DATABASE STORAGE")
    print("=" * 60)
    
    # 1. Reset local embedded database storage
    if os.path.exists(QDRANT_LOCAL_PATH):
        print(f"[*] Deleting local embedded Qdrant database folder: {QDRANT_LOCAL_PATH}")
        try:
            shutil.rmtree(QDRANT_LOCAL_PATH)
            print("Status: [OK] Local DB storage deleted successfully.")
        except Exception as e:
            print(f"Status: [ERROR] Could not delete folder: {e}")
    else:
        print("[*] No local embedded storage found.")

    # 2. Reset dockerized database collection
    try:
        client = QdrantClient(host="localhost", port=6333, timeout=3)
        # Attempt to delete collection if exists
        client.delete_collection(collection_name=QDRANT_COLLECTION)
        print(f"[*] Deleted Qdrant server collection: '{QDRANT_COLLECTION}'")
        print("Status: [OK] Server collection deleted.")
    except Exception:
        print("[*] Dockerized Qdrant is currently offline. Skipping collection deletion.")

    print("=" * 60)
    print("  Vector Database reset successfully.")
    print("=" * 60)

if __name__ == "__main__":
    reset_db()
