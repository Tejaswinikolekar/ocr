import streamlit as st
import pandas as pd
import time
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="PDF to Excel Extractor",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Attractive Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff3333;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.3);
    }
    .uploadedFile {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/pdf-2--v1.png", width=80)
    st.title("Settings & Help")
    st.markdown("---")
    st.markdown("### How to use:")
    st.markdown("1. **Upload** your PDF file.")
    st.markdown("2. Click **Extract Fields**.")
    st.markdown("3. **Preview** the data table.")
    st.markdown("4. **Download** your Excel sheet.")
    st.markdown("---")
    st.info("💡 **Tip:** Works best with text-based digital PDFs.")

# --- Main App Header ---
st.title("📊 PDF to Excel Field Extractor")
st.markdown("Transform your unstructured PDF documents into clean, structured Excel spreadsheets effortlessly.")
st.markdown("---")

# --- File Uploader Box ---
uploaded_file = st.file_uploader(
    "Choose a PDF file", 
    type="pdf", 
    help="Drag and drop your PDF here"
)

if uploaded_file is not None:
    # Display file details in a nice container
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"**File Loaded:** `{uploaded_file.name}`")
    with col2:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.metric(label="File Size", value=f"{file_size_kb:.1f} KB")

    st.markdown("###")

    # Action Button
    if st.button("🚀 Extract Fields & Convert"):
        with st.spinner("Extracting data from PDF... Please wait."):
            # Simulate processing time (Replace this with your actual pdfplumber function)
            time.sleep(1.5) 
            
            # --- MOCK DATA (Replace with your actual extraction DataFrame) ---
            data = {
                "Page": [1, 1, 2, 2],
                "Field Name": ["Invoice Number", "Total Amount", "Vendor Name", "Date"],
                "Extracted Value": ["INV-2026-001", "$1,250.00", "Acme Corp", "2026-06-06"]
            }
            df = pd.DataFrame(data)
            # -------------------------------------------------------------

        st.balloons() # Fun celebratory animation on success
        st.markdown("### ✨ Extracted Data Preview")
        st.dataframe(df, use_container_width=True)

        # Convert DataFrame to Excel format in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extracted Data')
        excel_data = output.getvalue()

        st.markdown("---")
        
        # Styled Download Button
        st.download_button(
            label="📥 Download Excel Spreadsheet (.xlsx)",
            data=excel_data,
            file_name=f"{uploaded_file.name.split('.')[0]}_extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
