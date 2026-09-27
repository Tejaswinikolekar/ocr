import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="Multi-Page Bill Data Extractor",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Modern Indigo/Slate Custom UI Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stButton>button {
        width: 100%;
        background-color: #6366f1;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #4f46e5;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    .metric-card {
        background-color: #1e293b;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #334155;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/document--v1.png", width=70)
    st.title("Extractor Studio")
    st.markdown("---")
    st.markdown("### 🔍 Target Fields Covered:")
    st.markdown("""
    * **Identifiers:** CA No, Bill No, Meter No, Address
    * **Loads & Demand:** Sanction/Connected Load, RMD, BMD, Contract/Billing Demand
    * **Tariffs & Units:** Tariff Category, Tariff, Units Consumed, Month, Year
    * **Financials:** Bill Amount, Duty, Discounts, DPC, TOD Charges, Supply Co.
    """)
    st.markdown("---")
    st.info("💡 **Pro Tip:** Each page of the PDF will be processed as an individual record row.")

# --- Main App Header ---
st.title("📑 Comprehensive PDF Field Extractor")
st.markdown("Extract all utility and tariff fields across **every page** of your document into a unified Excel database.")
st.markdown("---")

# --- Function to Extract Fields from a Single Page Text ---
def extract_fields_from_text(page_text, page_number):
    def find_pattern(regex, text, default=""):
        match = re.search(regex, text, re.IGNORECASE)
        return match.group(1).strip() if match else default

    # Map all target fields using smart regular expressions
    data = {
        "Page No": page_number,
        "CA No": find_pattern(r'(?:CA\s*No\.?|Consumer\s*No\.?|Account\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9]+)', page_text),
        "Bill No": find_pattern(r'(?:Bill\s*No\.?|Invoice\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9]+)', page_text),
        "Meter no": find_pattern(r'(?:Meter\s*No\.?|Meter\s*Number)\s*[:\-]?\s*([A-Za-z0-9]+)', page_text),
        "Address": find_pattern(r'(?:Address|Location)\s*[:\-]?\s*([^\n]+)', page_text),
        "Sanction Load": find_pattern(r'(?:Sanction(?:ed)?\s*Load)\s*[:\-]?\s*([\d\.\s\w]+)', page_text),
        "Connected load": find_pattern(r'(?:Connected\s*Load)\s*[:\-]?\s*([\d\.\s\w]+)', page_text),
        "Security Deposit": find_pattern(r'(?:Security\s*Deposit)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "RMD": find_pattern(r'(?:RMD)\s*[:\-]?\s*([\d\.]+)', page_text),
        "BMD": find_pattern(r'(?:BMD)\s*[:\-]?\s*([\d\.]+)', page_text),
        "Power Factor": find_pattern(r'(?:Power\s*Factor|P\.?F\.?)\s*[:\-]?\s*([\d\.]+)', page_text),
        "Contract Demand": find_pattern(r'(?:Contract\s*Demand|C\.?D\.?)\s*[:\-]?\s*([\d\.\s\w]+)', page_text),
        "Billing Demand": find_pattern(r'(?:Billing\s*Demand)\s*[:\-]?\s*([\d\.\s\w]+)', page_text),
        "Tariff category": find_pattern(r'(?:Tariff\s*Category|Category)\s*[:\-]?\s*([A-Za-z0-9\-\/\s]+)', page_text),
        "Tariff": find_pattern(r'(?<!Category\s)(?:Tariff)\s*[:\-]?\s*([A-Za-z0-9\-\/\s]+)', page_text),
        "Units Consumed/Billed Unit": find_pattern(r'(?:Units?\s*Consumed|Billed\s*Units?|Consumption|Units)\s*[:\-]?\s*([\d\.]+)', page_text),
        "Month": find_pattern(r'(?:Month)\s*[:\-]?\s*([A-Za-z]+)', page_text),
        "Year": find_pattern(r'(?:Year)\s*[:\-]?\s*(\d{4})', page_text),
        "Current month bill Amount Rs": find_pattern(r'(?:Current\s*Bill\s*Amount|Net\s*Amount|Total\s*Bill\s*Amount|Amount\s*Payable)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "Gov Electricity Duty": find_pattern(r'(?:Electricity\s*Duty|Govt\.?\s*Duty)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "Digital payment discount": find_pattern(r'(?:Digital\s*Payment\s*Discount|Online\s*Discount)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "DELAYED PAYMENT CHARGES (DPC)": find_pattern(r'(?:Delayed\s*Payment\s*Charges|DPC)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "Prompt payment discount": find_pattern(r'(?:Prompt\s*Payment\s*Discount|PPD)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "TOD Charges": find_pattern(r'(?:TOD\s*Charges?)\s*[:\-]?\s*([\d\.,]+)', page_text),
    }

    # Supply Company Auto-Detection
    if "BEST" in page_text:
        data["Supply Co."] = "BEST"
    elif "ADANI" in page_text:
        data["Supply Co."] = "Adani"
    elif "TATA" in page_text:
        data["Supply Co."] = "Tata"
    elif "MSEDCL" in page_text or "MAHAVITARAN" in page_text:
        data["Supply Co."] = "MSEDCL"
    else:
        data["Supply Co."] = "Unknown"

    return data

# --- File Uploader Widget ---
uploaded_file = st.file_uploader("Upload your multi-page PDF document", type="pdf")

if uploaded_file is not None:
    st.success(f"Successfully loaded: **{uploaded_file.name}**")
    
    if st.button("🚀 Process All Pages & Extract Fields"):
        extracted_rows = []
        
        # Open PDF and loop through every single page
        with pdfplumber.open(uploaded_file) as pdf:
            total_pages = len(pdf.pages)
            
            # Progress Bar UI element
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for index, page in enumerate(pdf.pages):
                status_text.text(f"Extracting data from page {index + 1} of {total_pages}...")
                page_text = page.extract_text() or ""
                
                # Extract dictionary for this page
                page_data = extract_fields_from_text(page_text, index + 1)
                extracted_rows.append(page_data)
                
                # Update progress bar
                progress_bar.progress((index + 1) / total_pages)
            
            status_text.text("Extraction completed successfully!")

        # Convert all rows into a complete Pandas DataFrame
        df = pd.DataFrame(extracted_rows)

        st.markdown("---")
        st.subheader("📊 Extracted Data Matrix (All Pages)")
        
        # Display DataFrame interactively
        st.dataframe(df, use_container_width=True)

        # Prepare Excel data in memory using openpyxl
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extracted Bill Data')
        excel_data = output.getvalue()

        st.markdown("---")
        
        # Download Button Container
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("Your spreadsheet is ready with all fields mapped across your document pages.")
        with col2:
            st.download_button(
                label="📥 Download Complete Excel File",
                data=excel_data,
                file_name=f"{uploaded_file.name.split('.')[0]}_all_pages_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
