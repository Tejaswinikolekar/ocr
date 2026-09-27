import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="Utility Bill Extractor",
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
    st.markdown("### 🛠️ Troubleshooting Tip:")
    st.markdown("If a field is missed, check the **Raw Text View** expander below the table to see how your bill structures its text labels.")

# --- Main App Header ---
st.title("⚡ Smart Electricity Bill Extractor")
st.markdown("Extract precise utility fields from your multi-page PDF bills into clean Excel sheets.")
st.markdown("---")

# --- Precision Extraction Logic ---
def extract_fields_from_text(page_text, page_number):
    def find_pattern(regex, text, default=""):
        match = re.search(regex, text, re.IGNORECASE)
        return match.group(1).strip() if match else default

    data = {
        "Page No": page_number,
        # Look for 9 to 12 digit consumer/CA numbers typically found in utility bills
        "CA No": find_pattern(r'(?:CA\s*No\.?|Consumer\s*No\.?|Account\s*No\.?|Cons\s*No\.?)\s*[:\-]?\s*([0-9]{8,15})', page_text),
        "Bill No": find_pattern(r'(?:Bill\s*No\.?|Invoice\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9\-]{5,20})', page_text),
        "Meter no": find_pattern(r'(?:Meter\s*No\.?|Meter\s*Number)\s*[:\-]?\s*([A-Za-z0-9]+)', page_text),
        "Address": find_pattern(r'(?:Address|Cons\.?\s*Name\s*&?\s*Address)\s*[:\-]?\s*([^\n\r]+)', page_text),
        
        # Look specifically for loads followed by KW, KVA, or HP
        "Sanction Load": find_pattern(r'(?:Sanction(?:ed)?\s*Load)\s*[:\-]?\s*([\d\.]+\s*(?:KW|KVA|HP))', page_text),
        "Connected load": find_pattern(r'(?:Connected\s*Load)\s*[:\-]?\s*([\d\.]+\s*(?:KW|KVA|HP))', page_text),
        
        "Security Deposit": find_pattern(r'(?:Security\s*Deposit|SD)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "RMD": find_pattern(r'(?:RMD)\s*[:\-]?\s*([\d\.]+)', page_text),
        "BMD": find_pattern(r'(?:BMD)\s*[:\-]?\s*([\d\.]+)', page_text),
        "Power Factor": find_pattern(r'(?:Power\s*Factor|P\.?F\.?)\s*[:\-]?\s*([\d\.]+)', page_text),
        "Contract Demand": find_pattern(r'(?:Contract\s*Demand|C\.?D\.?)\s*[:\-]?\s*([\d\.]+\s*(?:KW|KVA))', page_text),
        "Billing Demand": find_pattern(r'(?:Billing\s*Demand)\s*[:\-]?\s*([\d\.]+\s*(?:KW|KVA))', page_text),
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

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload your electricity bill PDF", type="pdf")

if uploaded_file is not None:
    st.success(f"File uploaded successfully: **{uploaded_file.name}**")
    
    if st.button("🚀 Process & Extract Fields"):
        extracted_rows = []
        raw_pages_text = {}
        
        with pdfplumber.open(uploaded_file) as pdf:
            total_pages = len(pdf.pages)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for index, page in enumerate(pdf.pages):
                status_text.text(f"Processing page {index + 1} of {total_pages}...")
                page_text = page.extract_text() or ""
                
                raw_pages_text[index + 1] = page_text # Save for debugging view
                
                page_data = extract_fields_from_text(page_text, index + 1)
                extracted_rows.append(page_data)
                
                progress_bar.progress((index + 1) / total_pages)
            
            status_text.text("Extraction completed!")

        df = pd.DataFrame(extracted_rows)

        st.markdown("---")
        st.subheader("📊 Extracted Data Preview")
        st.dataframe(df, use_container_width=True)

        # Excel Export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extracted Data')
        excel_data = output.getvalue()

        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.download_button(
                label="📥 Download Excel Spreadsheet (.xlsx)",
                data=excel_data,
                file_name=f"{uploaded_file.name.split('.')[0]}_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- Debug Expander to view raw text extracted by PDF ---
        with st.expander("🔍 View Raw Text Extracted from PDF (For Troubleshooting)"):
            for p_num, p_text in raw_pages_text.items():
                st.markdown(f"**Page {p_num} Raw Text:**")
                st.text(p_text)
