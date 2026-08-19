import os
import sys
import time
import streamlit as st
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from rag_system.config.settings import RetrieverConfig
from rag_system.retriever.pipeline import MedicalRetriever
from rag_system.retriever.generator import MedicalGenerator
from rag_system.retriever.prompt_builder import build_rag_prompt

# -----------------------------------------------------------------------------
# 1. STREAMLIT PAGE CONFIGURATION & THEME
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Medical RAG AI Chatbot — WHO Guidelines",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Medical CSS styling
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Header Section */
    .header-container {
        display: flex;
        align-items: center;
        gap: 20px;
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }
    .header-text h1 {
        color: #38bdf8 !important;
        font-size: 28px !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }
    .header-text p {
        color: #94a3b8;
        font-size: 15px;
        margin: 4px 0 0 0 !important;
    }
    
    /* AI Medical Recommendation Box */
    .recommendation-box {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 28px;
        border-left: 6px solid #0284c7;
        box-shadow: 0 10px 25px -5px rgba(2, 132, 199, 0.08), 0 8px 10px -6px rgba(2, 132, 199, 0.08);
        margin-bottom: 25px;
    }
    .recommendation-title {
        color: #0369a1;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .recommendation-content {
        color: #334155;
        font-size: 16px;
        line-height: 1.7;
    }
    
    /* Source Chunks Styles */
    .source-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .source-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* Metric KPI Cards */
    .metric-container {
        display: flex;
        gap: 15px;
        margin-bottom: 15px;
        margin-top: 10px;
    }
    .metric-card {
        flex: 1;
        background: #f1f5f9;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    .metric-val {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-lbl {
        font-size: 10px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CACHED RESOURCES (LOAD ONCE)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_medical_retriever(top_k_initial, top_k_final, similarity_threshold, sort_by_page, cohere_key):
    """Load and cache the Qdrant retriever pipeline."""
    cfg = RetrieverConfig(
        top_k_initial=top_k_initial,
        top_k_final=top_k_final,
        similarity_threshold=similarity_threshold,
        sort_by_page=sort_by_page
    )
    try:
        retriever = MedicalRetriever(cfg=cfg, cohere_api_key=cohere_key)
        return retriever, None
    except Exception as e:
        return None, str(e)

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONFIGURATION (NO API INPUTS)
# -----------------------------------------------------------------------------
# Fetch keys from environment loaded by python-dotenv
cohere_api_key = os.environ.get("COHERE_API_KEY", "")
groq_api_key = os.environ.get("GROQ_API_KEY", "")

# Initialize example prompt state
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

with st.sidebar:
    # Logo
    logo_path = os.path.join("assets", "medical_logo.jpg")
    if os.path.exists(logo_path):
        st.image(Image.open(logo_path), use_container_width=True)
    else:
        st.title("🩺 Medical RAG Chat")
        
    st.markdown("---")
    
    # 3.1 Model Selection Controls
    st.header("🤖 Model Selection")
    model_choice = st.selectbox(
        "Generation Model",
        options=["Cloud API (Groq)", "Qwen 3B (Colab Server)"],
        index=0,
        help="Select whether to use the high-performance Groq Cloud API or your custom-tuned Qwen 3B model running on Google Colab."
    )
    st.markdown("---")

    # 3.2 Hyperparameters sliders
    st.header("🎛️ RAG Parameters")
    
    similarity_threshold = st.slider(
        "Similarity Threshold (Min Score)",
        min_value=0.10,
        max_value=0.80,
        value=0.30,
        step=0.05,
        help="Higher values return fewer, more precise chunks. Lower values return broader context."
    )
    
    top_k_final = st.slider(
        "Top K Chunks (Final Context)",
        min_value=2,
        max_value=10,
        value=5,
        step=1,
        help="The final number of context blocks provided to the LLM."
    )
    
    sort_by_page = st.checkbox(
        "Sort Chunks by Page Number",
        value=True,
        help="Sort retrieved paragraphs in page order to present cohesive chronological text to the LLM."
    )
    
    st.markdown("---")
    
    # 3.2 Quick Guidelines reference / examples
    st.header("💡 Clinical Example Queries")
    example_queries = [
        "What is the recommended second-line treatment for type 2 diabetes when metformin fails?",
        "When should NPH insulin be introduced in non-pregnant adults?",
        "Is there a preference between insulin glargine and NPH insulin in terms of safety?",
        "What are the PICO questions and ranked outcomes for blood glucose control?"
    ]
    
    for idx, ex in enumerate(example_queries, 1):
        if st.button(f"Example {idx}", key=f"ex_{idx}", help=ex, use_container_width=True):
            st.session_state.current_prompt = ex
            st.rerun()
            
    st.markdown("---")
    
    # Clear conversation history
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_prompt = None
        st.rerun()

# -----------------------------------------------------------------------------
# 4. INITIALIZE RETRIEVER
# -----------------------------------------------------------------------------
retriever, load_error = get_medical_retriever(
    top_k_initial=top_k_final * 4,
    top_k_final=top_k_final,
    similarity_threshold=similarity_threshold,
    sort_by_page=sort_by_page,
    cohere_key=cohere_api_key
)

if load_error:
    st.error(f"❌ Failed to initialize Qdrant vector database: {load_error}")
    st.info("Please run the ingestion pipeline to build the index: `python scripts/ingest.py`")
    st.stop()

# Initialize Chat Messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------------------------------------------------------
# 5. HEADER COMPONENT
# -----------------------------------------------------------------------------
st.markdown(f"""
<div class="header-container">
    <div class="header-text">
        <h1>🩺 WHO Guidelines Qdrant RAG Assistant</h1>
        <p>Production-Grade Clinical Chatbot with Automated Failover Engine</p>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. RENDER CHAT HISTORY
# -----------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Show RAG Metadata & Sources inside the Assistant bubble
        if msg["role"] == "assistant":
            # Status Badge
            st.markdown(msg["status"], unsafe_allow_html=True)
            
            # Metrics Dashboard
            st.markdown(msg["metrics_html"], unsafe_allow_html=True)
            
            # Chunks Expander
            if msg.get("chunks"):
                with st.expander("📚 View Supporting WHO Guidelines Chunks"):
                    for idx, chunk in enumerate(msg["chunks"], 1):
                        p_start = chunk["metadata"].get("page_start", "N/A")
                        p_end = chunk["metadata"].get("page_end", p_start)
                        page_str = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}-{p_end}"
                        chapter = chunk["metadata"].get("chapter", "General Guidelines")
                        section = chunk["metadata"].get("section", "")
                        
                        st.markdown(f"**{idx}. WHO Guidelines {page_str} | {chapter} > {section} (Similarity: {chunk['score']:.4f})**")
                        st.markdown(chunk["content"])
                        
                        if chunk.get("table_references"):
                            st.caption(f"📊 **Associated Tables:** {', '.join(chunk['table_references'])}")
                        
                        if chunk.get("figure_references"):
                            st.markdown("📷 **Associated Images:**")
                            for fig in chunk["figure_references"]:
                                fig_path = fig.get("image_path")
                                caption = fig.get("caption", "Figure reference")
                                if fig_path and os.path.exists(fig_path):
                                    st.image(Image.open(fig_path), caption=caption, use_container_width=True)
                        st.markdown("---")

# -----------------------------------------------------------------------------
# 7. USER INPUT & CHATBOT FLOW
# -----------------------------------------------------------------------------
# Capture input (either from chat box or examples clicked)
chat_input_val = st.chat_input("Ask a clinical guideline question...")
user_query = None

if st.session_state.current_prompt:
    user_query = st.session_state.current_prompt
    st.session_state.current_prompt = None  # Reset example prompt
elif chat_input_val:
    user_query = chat_input_val

if user_query:
    # 7.1 Show User Message
    with st.chat_message("user"):
        st.markdown(user_query)
    
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    # 7.2 Run RAG and Generator
    with st.chat_message("assistant"):
        with st.spinner("🔍 Querying Qdrant and generating clinical recommendation..."):
            t0 = time.time()
            
            # Retrieve from Qdrant Vector DB
            search_result = retriever.retrieve(
                question=user_query,
                top_k=top_k_final,
                similarity_threshold=similarity_threshold
            )
            
            latency = search_result.latency_breakdown_ms
            retrieved_chunks = search_result.chunks
            
            # Format Prompt
            prompt = build_rag_prompt(user_query, retrieved_chunks)
            
            # LLM Text Generation
            t_gen_start = time.time()
            
            generator = MedicalGenerator(
                groq_api_key=groq_api_key,
                groq_model="openai/gpt-oss-120b"
            )
            
            answer_text = generator.generate_answer(
                query=user_query,
                chunks=retrieved_chunks,
                model_choice=model_choice
            )
            
            gen_latency_ms = (time.time() - t_gen_start) * 1000
            latency["generation_ms"] = gen_latency_ms
            latency["total_ms"] += gen_latency_ms
            
            # Connection Status HTML
            if model_choice == "Qwen 3B (Colab Server)":
                status_html = """<div style="margin-top: 10px;"><span style="color: #2563eb; font-weight: bold; background-color: #dbeafe; padding: 4px 10px; border-radius: 9999px; font-size: 12px;">💻 Colab: Using custom Qwen 3B (MedQuad)</span></div>"""
            elif generator.used_fallback:
                status_html = """<div style="margin-top: 10px;"><span style="color: #d97706; font-weight: bold; background-color: #fef3c7; padding: 4px 10px; border-radius: 9999px; font-size: 12px;">⚠️ Fallback: Using local Ollama model (llama3)</span></div>"""
            else:
                status_html = """<div style="margin-top: 10px;"><span style="color: #059669; font-weight: bold; background-color: #d1fae5; padding: 4px 10px; border-radius: 9999px; font-size: 12px;">🟢 Connected: Using Groq Cloud API (GPT-OSS-120B)</span></div>"""
            
            # Metrics HTML
            total_time_ms = latency.get("total_ms", 0.0)
            metrics_html = f"""
            <div class="metric-container">
                <div class="metric-card">
                    <div class="metric-val">{len(retrieved_chunks)} / {search_result.total_initial_found}</div>
                    <div class="metric-lbl">Chunks Used / Candidates</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{latency.get('search_ms', 0.0):.1f} ms</div>
                    <div class="metric-lbl">Qdrant Search</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{latency.get('generation_ms', 0.0):.1f} ms</div>
                    <div class="metric-lbl">LLM Generation</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val">{total_time_ms / 1000:.2f} s</div>
                    <div class="metric-lbl">Total Time</div>
                </div>
            </div>
            """
            
            # Show Answer
            st.markdown(answer_text)
            st.markdown(status_html, unsafe_allow_html=True)
            st.markdown(metrics_html, unsafe_allow_html=True)
            
            # Show Chunks inside Expander
            serializable_chunks = []
            if retrieved_chunks:
                with st.expander("📚 View Supporting WHO Guidelines Chunks"):
                    for idx, chunk in enumerate(retrieved_chunks, 1):
                        p_start = chunk.metadata.get("page_start", "N/A")
                        p_end = chunk.metadata.get("page_end", p_start)
                        page_str = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}-{p_end}"
                        chapter = chunk.metadata.get("chapter", "General Guidelines")
                        section = chunk.metadata.get("section", "")
                        
                        st.markdown(f"**{idx}. WHO Guidelines {page_str} | {chapter} > {section} (Similarity: {chunk.score:.4f})**")
                        st.markdown(chunk.content)
                        
                        # Serialize for history saving
                        serializable_chunks.append({
                            "content": chunk.content,
                            "score": chunk.score,
                            "metadata": {
                                "page_start": p_start,
                                "page_end": p_end,
                                "chapter": chapter,
                                "section": section
                            },
                            "table_references": chunk.table_references,
                            "figure_references": chunk.figure_references
                        })
                        
                        if chunk.table_references:
                            st.caption(f"📊 **Associated Tables:** {', '.join(chunk.table_references)}")
                        
                        if chunk.figure_references:
                            st.markdown("📷 **Associated Images:**")
                            for fig in chunk.figure_references:
                                fig_path = fig.get("image_path")
                                caption = fig.get("caption", "Figure reference")
                                if fig_path and os.path.exists(fig_path):
                                    st.image(Image.open(fig_path), caption=caption, use_container_width=True)
                        st.markdown("---")
            else:
                st.warning("No relevant guideline blocks found matching the similarity threshold.")

            # Append to session state history
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer_text,
                "status": status_html,
                "metrics_html": metrics_html,
                "chunks": serializable_chunks
            })

# -----------------------------------------------------------------------------
# 8. INITIAL STATE SCREEN (SHOW ONLY WHEN HISTORY IS EMPTY)
# -----------------------------------------------------------------------------
if not st.session_state.messages:
    st.info("👈 Select an example query from the sidebar or type a clinical scenario below to start a chat session.")
    
    st.subheader("📊 System Information")
    c1, c2, c3 = st.columns(3)
    
    if retriever.vector_store.client:
        qdrant_status = "🟢 Connected (Embedded)" if retriever.vector_store.is_embedded else "🟢 Connected (Docker)"
    else:
        qdrant_status = "🔴 Disconnected"
        
    with c1:
        st.metric("Total Indexed Chunks", f"{retriever.vector_store.count()} chunks")
    with c2:
        st.metric("Vector Dimension", f"{retriever.cfg.embedding_dimension} (Cohere / FastEmbed)")
    with c3:
        st.metric("Qdrant Database Status", qdrant_status)
        
    st.markdown("""
    ### 📖 Guidelines Covered:
    This RAG system indexes the official **WHO guidelines on second- and third-line medicines and types of insulin for the control of blood glucose levels in non-pregnant adults with diabetes mellitus**. 
    
    It allows doctors to ask about:
    1. **Second-line treatments** when Metformin fails.
    2. **Third-line options** (choice between Sulfonylureas, DPP-4 inhibitors, SGLT-2 inhibitors, and GLP-1 receptor agonists).
    3. **Insulin selection** (human NPH insulin vs. long-acting insulin analogues such as Glargine or Detemir).
    4. **Safety and outcomes** (risks of severe hypoglycaemia, weight gain, cardiovascular events, and cost-effectiveness).
    """)
