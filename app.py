import os
import sys

# Configure python path to prioritize internal src/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# Import and execute Streamlit application core
import rag_system.app
