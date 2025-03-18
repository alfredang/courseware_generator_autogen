import streamlit as st
import os
import tempfile
from config_loader import load_shared_resources
from redis_indexing import run_indexing_with_files
from redis_querying import initialize_chat_pipeline, run_chat_query
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import ChatMemoryBuffer
import asyncio
from retrieval_workflow import create_tsc_assessments
import base64

st.set_page_config(
    page_title="RAG Assessment Tool",
    page_icon="🔍",
    layout="wide"
)

config, embed_model = load_shared_resources()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    st.session_state.memory = ChatMemoryBuffer.from_defaults(token_limit=8000)

if "pipeline" not in st.session_state:
    st.session_state.pipeline = initialize_chat_pipeline(embed_model, config)

if "selected_model" not in st.session_state:
    st.session_state.selected_model = "GPT-4o Mini (Default)"

st.title("RAG Assessment Tool")

# Move navigation to the sidebar
page = st.sidebar.radio(
    "Navigation",
    ["Document Indexing", "Document Querying", "Document Generation"],
    index=0
)

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(bin_file)}">{file_label}</a>'

# ─────────────────────────────────────────────────────────────────────────────
# 1. DOCUMENT INDEXING PAGE
# ─────────────────────────────────────────────────────────────────────────────
if page == "Document Indexing":
    st.header("📤 Document Indexing")
    st.markdown("""
    Upload PDF documents to index them for future querying.
    The system will parse and create embeddings for document content.
    """)
    
    uploaded_files = st.file_uploader(
        "Upload your PDF documents", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    
    chunk_size = 3  
    chunk_overlap = 1
    
    index_button = st.button(
        "Process and Index Documents", 
        type="primary", 
        disabled=len(uploaded_files) == 0
    )
    
    status_placeholder = st.empty()
    
    if uploaded_files:
        file_list = ", ".join([file.name for file in uploaded_files])
        st.info(f"Selected files: {file_list}")
    
    if index_button and uploaded_files:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                file_paths.append(file_path)
            
            status_placeholder.info("Indexing in progress... This may take a few minutes.")
            
            try:
                with st.spinner("Processing documents..."):
                    node_count = run_indexing_with_files(file_paths, embed_model)
                status_placeholder.success(f"✅ Indexing complete! {node_count} nodes indexed.")
                st.balloons()
            
            except Exception as e:
                status_placeholder.error(f"❌ Indexing failed: {str(e)}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. DOCUMENT QUERYING (CHAT INTERFACE) PAGE
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Document Querying":
    st.header("💬 Chat with Your Documents")
    st.markdown("""
    Ask questions about your indexed documents and get answers based on their content.
    The system will retrieve relevant information and generate responses using Gemini LLM.
    """)
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.memory = ChatMemoryBuffer.from_defaults(token_limit=8000)
        st.experimental_rerun()
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    prompt = st.chat_input("Ask something about your documents...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Thinking..."):
                response = run_chat_query(
                    prompt, 
                    st.session_state.pipeline,
                    st.session_state.memory,
                    retrieval_mode="hybrid",
                    top_k=6
                )
                response_content = response.message.content
                st.session_state.messages.append({"role": "assistant", "content": response_content})
                message_placeholder.markdown(response_content)
    
    if not st.session_state.messages:
        st.info("👋 Send a message to start chatting about your documents!")

# ─────────────────────────────────────────────────────────────────────────────
# 3. DOCUMENT GENERATION PAGE
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Document Generation":
    st.header("🔄 TSC Document Generation")
    st.markdown("""
    Upload a Technical Skills Checklist (TSC) file to automatically generate assessment documents.
    The system will parse the TSC, create learning units, and generate assessment materials.
    """)
    
    model_options = ["GPT-4o Mini (Default)", "GPT-4o", "Claude-3-Opus"]
    selected_model = st.selectbox("Select LLM Model", options=model_options, index=0)
    st.session_state.selected_model = selected_model
    
    tsc_file = st.file_uploader(
        "Upload your TSC document", 
        type=["docx", "pdf", "txt"], 
        help="Upload a Technical Skills Checklist document"
    )
    
    if tsc_file:
        st.write(f"Selected file: {tsc_file.name}")
        
        process_button = st.button("Process TSC and Generate Documents", type="primary")
        
        if process_button:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save with proper extension - this is key!
                file_path = os.path.join(temp_dir, tsc_file.name)
                with open(file_path, "wb") as f:
                    f.write(tsc_file.getvalue())
                
                os.makedirs("json_output", exist_ok=True)
                os.makedirs("output_json", exist_ok=True)
                
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                progress_text.text("Processing TSC document...")
                progress_bar.progress(25)
                
                try:
                    # Pass the actual file path with extension
                    asyncio.run(create_tsc_assessments(file_path))

                    
                    progress_text.text("Generating documents...")
                    progress_bar.progress(75)
                    progress_text.text("Completed document generation!")
                    progress_bar.progress(100)
                    st.success("✅ Document generation completed successfully!")
                    
                    st.subheader("Download Generated Documents")
                    output_files = []
                    for root, dirs, files in os.walk("output_documents"):
                        for file in files:
                            if file.endswith(".docx") or file.endswith(".pdf"):
                                output_files.append(os.path.join(root, file))
                    
                    if output_files:
                        for file_path in output_files:
                            st.markdown(
                                get_binary_file_downloader_html(
                                    file_path, 
                                    f"Download {os.path.basename(file_path)}"
                                ), 
                                unsafe_allow_html=True
                            )
                    else:
                        st.warning("No output documents found. Check the process output for details.")
                
                except Exception as e:
                    st.error(f"Error during document generation: {str(e)}")
                    st.error("Check logs for more details")