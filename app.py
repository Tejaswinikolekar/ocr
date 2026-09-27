import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="BEST & Utility Bill Extractor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Modern UI Styling ---
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
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/electricity.png", width=70)
    st.title("Bill Extractor Pro")
    st.markdown("---")
    st.markdown("### 📌 Features:")
    st.markdown("- **1 PDF Bill** = **1 Row** (all pages merged).")
    st.markdown("- Specialized pattern matching for BEST & MSEDCL bills.")
    st.markdown("- Strict data type separation (Numbers vs Text).")

# --- Main App Header ---
st.title("⚡ Precision Electricity Bill Extractor")
st.markdown("Extract accurate numerical and text fields from utility bills into clean single rows.")
st.markdown("---")

# --- Extraction Logic ---
def parse_single_bill(uploaded_file):
    full_text = ""
    
    # Merge text from all pages of the bill PDF
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    def find_num(regex_list, text, default="N/A"):
        for regex in regex_list:
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val:
                    return val
        return default

    def find_text(regex_list, text, default="N/A"):
        for regex in regex_list:
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val:
                    return val
        return default

    # Precision regex mapping based on actual bill layouts (like BEST / MSEDCL)
    data = {
        "Source File": uploaded_file.name,
        
        # Numbers
        "CA No": find_num([
            r'C\.?A\.?\s*No\.?\s*[:\-]?\s*([0-9]{6,12})',
            r'(?:Consumer\s*No\.?|CA\s*No\.?)\s*[:\-]?\s*([0-9]{6,12})'
        ], full_text),
        
        "Bill No": find_num([
            r'(?:Bill\s*No\.?|Invoice\s*No\.?|Bill\s*Number)\s*[:\-]?\s*([0-9A-Za-z\-]{5,20})'
        ], full_text),
        
        "Meter no": find_num([
            r'(?:Meter\s*No\.?|Meter\s*Number|Meter\s*ID)\s*[:\-]?\s*([0-9A-Za-z]{5,12})'
        ], full_text),
        
        # Text (Address)
        "Address": find_text([
            r'Billing\s*Address\s*:\s*([^\n\r]+(?:[\r\n]+[^\n\r]+){0,2})',
            r'(?:Service\s*Address|Billing\s*Address)\s*[:\-]?\s*([^\n\r]+)'
        ], full_text),
        
        # Numbers
        "Sanction Load": find_num([
            r'Sanctioned\s*Load\s*[:\-]?\s*([0-9\.]+)',
            r'(?:Sanction(?:ed)?\s*Load)\s*[:\-]?\s*([0-9\.]+)'
        ], full_text),
        
        "Connected load": find_num([r'(?:Connected\s*Load)\s*[:\-]?\s*([0-9\.]+)'], full_text),
        "Security Deposit": find_num([r'(?:Security\s*Deposit|SD)\s*[:\-]?\s*([\d\.,]+)'], full_text),
        "RMD": find_num([r'(?:RMD|Registered\s*Maximum\s*Demand)\s*[:\-]?\s*([0-9\.]+)'], full_text),
        "BMD": find_num([r'(?:BMD|Billing\s*Maximum\s*Demand)\s*[:\-]?\s*([0-9\.]+)'], full_text),
        "Power Factor": find_num([r'(?:Power\s*Factor|P\.?F\.?)\s*[:\-]?\s*([0-9\.]+)'], full_text),
        
        "Contract Demand": find_num([
            r'Contract\s*Demand\s*in\s*KVA\s*[:\-]?\s*([0-9\.]+)',
            r'(?:Contract\s*Demand|C\.?D\.?)\s*[:\-]?\s*([0-9\.]+)'
        ], full_text),
        
        "Billing Demand": find_num([
            r'Billing\s*Demand\s*in[^\n\r]*[\r\n]+\s*([0-9\.]+)',
            r'(?:Billing\s*Demand)\s*[:\-]?\s*([0-9\.]+)'
        ], full_text),
        
        # Text
        "Tariff category": find_text([
            r'Category\s*[:\-]?\s*([A-Za-z\s]+)',
            r'(?:Tariff\s*Category)\s*[:\-]?\s*([A-Za-z\s]+)'
        ], full_text),
        
        "Tariff": find_text([
            r'(?<!Category\s)Tariff\s*[:\-]?\s*([A-Za-z0-9\-\/\s]+)'
        ], full_text),
        
        # Numbers
        "Units Consumed/Billed Unit": find_num([
            r'kWh\s*[\r\n]+\s*[0-9\.]+\s*[0-9\.]+\s*[0-9\.]+\s*[0-9\.]+\s*([0-9\.]+)',
            r'(?:Units?\s*Consumed|Billed\s*Units?|Consumption|Total\s*Units?)\s*[:\-]?\s*([0-9\.]+)'
        ], full_text),
        
        # Text / Number
        "Month": find_text([
            r'Electricity\s*Bill\s*for\s*Month\s*of\s*([A-Za-z]+)',
            r'(?:Month|Billing\s*Month)\s*[:\-]?\s*([A-Za-z]{3,9})'
        ], full_text),
        
        "Year": find_num([
            r'Electricity\s*Bill\s*for\s*Month\s*of\s*[A-Za-z]+\s*(\d{4})',
            r'(?:Year|Billing\s*Year)\s*[:\-]?\s*(\d{4})'
        ], full_text),
        
        "Current month bill Amount Rs": find_num([
            r'Total\s*Current\s*Month\s*charges\s*\(?A\+B\)?\s*[:\-]?\s*([\d\.,]+)',
            r'(?:Current\s*Bill\s*Amount|Net\s*Amount|Total\s*Bill\s*Amount|Amount\s*Payable)\s*[:\-]?\s*([\d\.,]+)'
        ], full_text),
        
        "Gov Electricity Duty": find_num([
            r'(?:Electricity\s*Duty|Govt\.?\s*Duty|Ed\s*Duty)\s*[:\-]?\s*([\d\.,]+)'
        ], full_text),
        
        "Digital payment discount / (DPC)": find_num([
            r'Digital\s*Payment\s*Disc\.?\/ebill\s*disc[^\n\r]*?([-\d\.]+)',
            r'(?:Digital\s*Payment\s*Discount|Online\s*Discount|DPC)\s*[:\-]?\s*([-\d\.,]+)'
        ], full_text),
        
        "DELAYED PAYMENT CHARGES": find_num([
            r'Delayed\s*Payment\s*Charges[^\n\r]*?([-\d\.]+)',
            r'(?:Delayed\s*Payment\s*Charges|DPC)\s*[:\-]?\s*([\d\.,]+)'
        ], full_text),
        
        "Prompt payment discount": find_num([
            r'(?:Prompt\s*Payment\s*Discount|PPD)\s*[:\-]?\s*([\d\.,]+)'
        ], full_text),
        
        "TOD Charges": find_num([
            r'TOD\s*Charges\s*[:\-]?\s*([-\d\.,]+)',
            r'(?:TOD\s*Charges?|Time\s*of\s*Day\s*Charges?)\s*[:\-]?\s*([-\d\.,]+)'
        ], full_text),
        
        # Text (Supply Co.)
        "Supply Co.(BEST / Adani / Tata / MSEDCL)": (
            "BEST" if "BEST" in full_text else
            "Adani" if "ADANI" in full_text else
            "Tata" if "TATA" in full_text else
            "MSEDCL" if "MSEDCL" in full_text or "MAHAVITARAN" in full_text else
            "Unknown"
        )
    }

    return data, full_text

# --- Multiple File Uploader ---
uploaded_files = st.file_uploader("Upload your bill PDF(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    st.success(f"Successfully loaded **{len(uploaded_files)}** bill file(s).")
    
    if st.button("🚀 Process Bills to Single Rows"):
        all_rows = []
        raw_texts = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing bill {idx + 1} of {len(uploaded_files)}: {uploaded_file.name}")
            row_data, full_text = parse_single_bill(uploaded_file)
            all_rows.append(row_data)
            raw_texts[uploaded_file.name] = full_text
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_text.text("Processing completed successfully!")

        # Master DataFrame (1 Row per Bill PDF)
        df = pd.DataFrame(all_rows)

        st.markdown("---")
        st.subheader("📊 Structured Bill Summary (1 Row per Bill)")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Bill Summary')
        excel_data = output.getvalue()

        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("Your structured master Excel sheet is ready.")
        with col2:
            st.download_button(
                label="📥 Download Master Excel File",
                data=excel_data,
                file_name="electricity_bills_structured.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Raw Text Inspection Expander
        with st.expander("🔍 View Raw Text of Processed Bills (For Layout Verification)"):
            for fname, text in raw_texts.items():
                st.markdown(f"**File: {fname}**")
                st.text(text[:2500] + "\n... [truncated]")
