# Hackathon Project Context: Medical RAG AI Assistant

You are an expert AI software engineer assisting the developer in building a **Medical Retrieval-Augmented Generation (RAG) AI Assistant** for a hackathon. 

---

## 📌 Project Overview
We are building a RAG-based AI assistant for doctors. 
- **Goal:** Help doctors diagnose and recommend treatments based on patient inputs (symptoms, age, medical history, etc.) by retrieving information from a specific WHO guideline document.
- **Reference PDF Document:** `9789241550284-eng.pdf` (WHO Guidelines on second- and third-line medicines and types of insulin for the control of blood glucose levels in non-pregnant adults with diabetes mellitus).
- **Core Requirement:** The assistant **MUST** retrieve relevant information and explicitly reference the exact page numbers from the PDF in its answers so that the doctor can verify the sources.

---

## 🛠️ Tech Stack & Implementation Plan
For the hackathon, we want a fast, simple, and robust architecture:
1. **PDF Parsing & Extraction:** Extract text, tables, and section headings *along with their corresponding page numbers*.
2. **Chunking Strategy:** Chunk text by page or by paragraphs with overlapping sections, ensuring every chunk retains metadata containing:
   - `source_file`: `9789241550284-eng.pdf`
   - `page_number`: The actual PDF page number (1-indexed).
3. **Embeddings & Vector Database:** Use a lightweight, local, or fast-to-deploy vector database (e.g., ChromaDB, FAISS, or Qdrant) with an embedding model (e.g., OpenAI, Gemini, or HuggingFace local embeddings).
4. **LLM & Prompting:**
   - Query the LLM (Gemini or OpenAI) with the user's query and the retrieved chunks.
   - Instruct the LLM to write a concise clinical summary, recommendation, and list the exact pages used (e.g., "Based on WHO Guidelines page 12, ...").
5. **User Interface (UI):** A simple dashboard (e.g., Streamlit, Gradio, or a web frontend) where the doctor can type patient symptoms/age and see the diagnosis, recommendations, and source page numbers.

---

## 🚀 Key Guidelines for Agents Working on This Codebase
When writing code or assisting the developer, you must:
1. **Prioritize simplicity and speed** since this is for a hackathon. Prefer Python scripts, Streamlit/Gradio for the UI, and simple vector stores.
2. **Ensure page-number preservation** in the parsing and chunking code. Do not write chunking code that discards page numbers.
3. **Incorporate source citation** in the generation prompt. The LLM must be formatted to output page-number links/references.
4. **Be educational and helpful:** The developer has a basic understanding of RAG but is not an expert. Explain the steps clearly (Parsing -> Chunking -> Embedding -> Indexing -> Retrieval -> Generation).
5. **Always provide functional, modular code** that the developer can run directly.
