import os
import sys

# Configure python path to find the package src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rag_system.ingestion.pipeline import run_ingestion

if __name__ == "__main__":
    # Check if a custom PDF path was provided as an argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"[*] Using custom PDF path: {pdf_path}")
        run_ingestion(pdf_path)
    else:
        print("[*] Running ingestion with default PDF path.")
        run_ingestion()

