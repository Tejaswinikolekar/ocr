import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="Individual Bill Extractor",
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

# --- Sidebar Instructions ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/electricity.png", width=70)
    st.title("Bill Parser Studio")
    st.markdown("---")
    st.markdown("### 📌 How It Works:")
    st.markdown("1. Upload PDFs containing **one or multiple bills**.")
    st.markdown("2. The app scans page-by-page to isolate each bill.")
    st.markdown("3. Each detected bill populates **strictly one row**.")
    st.markdown("4. Download your structured Excel spreadsheet.")
    st.markdown("---")
    st.info("💡 Handles bulk PDFs where multiple consumer bills are bundled together.")

# --- Main App Header ---
st.title("⚡ Multi-Bill PDF Row Extractor")
st.markdown("Detect individual bills within your PDF documents and map each bill's details into its own distinct row.")
st.markdown("---")

# --- Extraction Logic for Individual Bills ---
def parse_bill_text(page_text, file_name, bill_index):
    def find_pattern(regex, text, default="N/A"):
        match = re.search(regex, text, re.IGNORECASE)
        return match.group(1).strip() if match else default

    # Extract fields for this specific bill/page
    data = {
        "Source File": file_name,
        "Bill Index": bill_index,
        "CA No": find_pattern(r'(?:CA\s*No\.?|Consumer\s*No\.?|Account\s*No\.?|Cons\s*No\.?)\s*[:\-]?\s*([0-9A-Za-z]{6,15})', page_text),
        "Bill No": find_pattern(r'(?:Bill\s*No\.?|Invoice\s*No\.?|Bill\s*Number)\s*[:\-]?\s*([0-9A-Za-z\-]{5,20})', page_text),
        "Meter no": find_pattern(r'(?:Meter\s*No\.?|Meter\s*Number|Meter\s*ID)\s*[:\-]?\s*([0-9A-Za-z]+)', page_text),
        "Address": find_pattern(r'(?:Address|Cons\.?\s*Name\s*&?\s*Address|Service\s*Address)\s*[:\-]?\s*([^\n\r]+)', page_text),
        "Sanction Load": find_pattern(r'(?:Sanction(?:ed)?\s*Load)\s*[:\-]?\s*([0-9\.]+\s*(?:KW|KVA|HP|kW|kVA))', page_text),
        "Connected load": find_pattern(r'(?:Connected\s*Load)\s*[:\-]?\s*([0-9\.]+\s*(?:KW|KVA|HP|kW|kVA))', page_text),
        "Security Deposit": find_pattern(r'(?:Security\s*Deposit|SD)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "RMD": find_pattern(r'(?:RMD|Registered\s*Maximum\s*Demand)\s*[:\-]?\s*([0-9\.]+)', page_text),
        "BMD": find_pattern(r'(?:BMD|Billing\s*Maximum\s*Demand)\s*[:\-]?\s*([0-9\.]+)', page_text),
        "Power Factor": find_pattern(r'(?:Power\s*Factor|P\.?F\.?)\s*[:\-]?\s*([0-9\.]+)', page_text),
        "Contract Demand": find_pattern(r'(?:Contract\s*Demand|C\.?D\.?)\s*[:\-]?\s*([0-9\.]+\s*(?:KW|KVA|kW|kVA))', page_text),
        "Billing Demand": find_pattern(r'(?:Billing\s*Demand)\s*[:\-]?\s*([0-9\.]+\s*(?:KW|KVA|kW|kVA))', page_text),
        "Tariff category": find_pattern(r'(?:Tariff\s*Category|Category)\s*[:\-]?\s*([A-Za-z0-9\-\/\s]+)', page_text),
        "Tariff": find_pattern(r'(?<!Category\s)(?:Tariff)\s*[:\-]?\s*([A-Za-z0-9\-\/\s]+)', page_text),
        "Units Consumed/Billed Unit": find_pattern(r'(?:Units?\s*Consumed|Billed\s*Units?|Consumption|Total\s*Units?)\s*[:\-]?\s*([0-9\.]+)', page_text),
        "Month": find_pattern(r'(?:Month|Billing\s*Month)\s*[:\-]?\s*([A-Za-z]{3,9})', page_text),
        "Year": find_pattern(r'(?:Year|Billing\s*Year)\s*[:\-]?\s*(\d{4})', page_text),
        "Current month bill Amount Rs": find_pattern(r'(?:Current\s*Bill\s*Amount|Net\s*Amount|Total\s*Bill\s*Amount|Amount\s*Payable|Net\s*Bill\s*Amount)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "Gov Electricity Duty": find_pattern(r'(?:Electricity\s*Duty|Govt\.?\s*Duty|Ed\s*Duty)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "Digital payment discount": find_pattern(r'(?:Digital\s*Payment\s*Discount|Online\s*Discount|E-Payment\s*Discount)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "DELAYED PAYMENT CHARGES (DPC)": find_pattern(r'(?:Delayed\s*Payment\s*Charges|DPC)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "Prompt payment discount": find_pattern(r'(?:Prompt\s*Payment\s*Discount|PPD)\s*[:\-]?\s*([\d\.,]+)', page_text),
        "TOD Charges": find_pattern(r'(?:TOD\s*Charges?|Time\s*of\s*Day\s*Charges?)\s*[:\-]?\s*([\d\.,]+)', page_text),
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
uploaded_files = st.file_uploader("Upload PDF bill(s)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    st.success(f"Loaded **{len(uploaded_files)}** PDF file(s) successfully.")
    
    if st.button("🚀 Process Bills & Generate Rows"):
        all_extracted_rows = []
        global_bill_counter = 1
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(uploaded_files)
        for f_idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Reading file {f_idx + 1} of {total_files}: {uploaded_file.name}")
            
            with pdfplumber.open(uploaded_file) as pdf:
                for p_idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    
                    # Basic check to ensure the page contains bill information (e.g. has CA No or Bill keywords)
                    if len(page_text.strip()) > 50:
                        bill_row = parse_bill_text(page_text, uploaded_file.name, global_bill_counter)
                        all_extracted_rows.append(bill_row)
                        global_bill_counter += 1
                        
            progress_bar.progress((f_idx + 1) / total_files)
            
        status_text.text("Processing complete!")

        # Convert to DataFrame where each detected bill gets its own row
        df = pd.DataFrame(all_extracted_rows)

        st.markdown("---")
        st.subheader("📊 Extracted Bills Table (Each Bill = 1 Row)")
        st.dataframe(df, use_container_width=True)

        # Excel Export in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Individual Bills')
        excel_data = output.getvalue()

        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("Your spreadsheet is formatted with individual rows per bill.")
        with col2:
            st.download_button(
                label="📥 Download Excel Spreadsheet",
                data=excel_data,
                file_name="individual_bills_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
