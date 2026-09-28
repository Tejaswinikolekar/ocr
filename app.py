from io import BytesIO
import json
import os
import time
from google import genai
from google.genai import types
import pdfplumber
import pandas as pd
from pydantic import BaseModel, Field
import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    page_title="High-Accuracy AI Bill Extractor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Modern UI Styling ---
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# --- Sidebar Configuration ---
with st.sidebar:
  st.image("https://img.icons8.com/color/96/electricity.png", width=70)
  st.title("AI Bill Extractor")
  st.markdown("---")

  # API Key Input for Gemini
  api_key_input = st.text_input(
      "Gemini API Key",
      type="password",
      help=(
          "Enter your Google Gemini API key. Alternatively, set it as an"
          " environment variable GEMINI_API_KEY."
      ),
  )

  st.markdown("---")
  st.markdown("### 📌 Specifications:")
  st.markdown("- **1 PDF Bill** = **1 Row** (all pages merged).")
  st.markdown("- **AI-Powered Extraction** with auto-retry resilience.")
  st.markdown("- Strict schema mapping with automated Excel export.")

# --- Main App Header ---
st.title("⚡ AI-Powered Utility Bill Extractor")
st.markdown(
    "Extract bills into precise numerical and text columns with **one row per"
    " bill** using Gemini."
)
st.markdown("---")


# --- Define Strict Output Schema using Pydantic ---
class UtilityBillSchema(BaseModel):
  CA_No: str = Field(
      description=(
          "Consumer Account Number, CA No, or Consumer No (e.g. 8-15 digits)"
      )
  )
  Bill_No: str = Field(description="Bill Number, Invoice Number, or ID")
  Meter_no: str = Field(description="Meter Number or Meter ID")
  Address: str = Field(
      description="Service Address or Consumer Name & Full Address"
  )
  Sanction_Load: str = Field(
      description="Sanctioned Load with units if available e.g. 5 kW"
  )
  Connected_load: str = Field(
      description="Connected Load with units if available"
  )
  Security_Deposit: str = Field(
      description="Security Deposit amount or SD value"
  )
  RMD: str = Field(description="Registered Maximum Demand (RMD)")
  BMD: str = Field(description="Billing Maximum Demand (BMD)")
  Power_Factor: str = Field(description="Power Factor or P.F. value")
  Contract_Demand: str = Field(description="Contract Demand or C.D.")
  Billing_Demand: str = Field(description="Billing Demand value")
  Tariff_category: str = Field(
      description="Tariff Category classification e.g. LT-I, Commercial, etc."
  )
  Tariff: str = Field(description="Tariff code or details")
  Units_Consumed: str = Field(
      description="Total Units Consumed, Billed Units, or Consumption amount"
  )
  Month: str = Field(description="Billing Month e.g. January, March")
  Year: str = Field(description="Billing Year e.g. 2026")
  Current_month_bill_Amount_Rs: str = Field(
      description=(
          "Current Bill Amount, Net Amount, Total Bill Amount, or Amount"
          " Payable"
      )
  )
  Gov_Electricity_Duty: str = Field(
      description="Government Electricity Duty or ED amount"
  )
  Digital_payment_discount: str = Field(
      description="Digital Payment Discount, Online Discount, or DPC"
  )
  DELAYED_PAYMENT_CHARGES: str = Field(
      description="Delayed Payment Charges or DPC amount"
  )
  Prompt_payment_discount: str = Field(
      description="Prompt Payment Discount or PPD amount"
  )
  TOD_Charges: str = Field(
      description="TOD Charges or Time of Day Charges amount"
  )
  Supply_Co: str = Field(
      description=(
          "Supply Company name: identify whether BEST, Adani, Tata, MSEDCL/Mahavitaran,"
          " or Unknown"
      )
  )


# --- Extraction Function using Gemini SDK with Exponential Back-off ---
def parse_bill_with_gemini(uploaded_file, api_key):
  # 1. Extract text from PDF using pdfplumber
  full_text = ""
  with pdfplumber.open(uploaded_file) as pdf:
    for page in pdf.pages:
      text = page.extract_text()
      if text:
        full_text += text + "\n"

  # 2. Configure Gemini Client
  client_kwargs = {}
  if api_key:
    client_kwargs["api_key"] = api_key
  elif os.environ.get("GEMINI_API_KEY"):
    client_kwargs["api_key"] = os.environ.get("GEMINI_API_KEY")

  client = genai.Client(**client_kwargs)

  prompt = f"""
    You are an expert data extraction assistant specialized in utility bills (MSEDCL, Adani, Tata, BEST, etc.).
    Extract all requested details accurately from the utility bill text provided below. If a value is missing or cannot be found, return "N/A".
    
    BILL TEXT CONTENT:
    {full_text}
    """

  # 3. Robust retry loop with exponential back-off (handles 503 spikes)
  max_retries = 4
  for attempt in range(max_retries):
    try:
      response = client.models.generate_content(
          model="gemini-3.8-flash",
          contents=prompt,
          config=types.GenerateContentConfig(
              response_mime_type="application/json",
              response_schema=UtilityBillSchema,
              temperature=0.0,
          ),
      )
      extracted_data = json.loads(response.text)
      extracted_data["Source File"] = uploaded_file.name
      return extracted_data, full_text
    except Exception as e:
      if attempt < max_retries - 1:
        sleep_time = 2 ** (
            attempt + 1
        )  # Wait longer each retry: 2s, 4s, 8s...
        time.sleep(sleep_time)
        continue
      else:
        st.error(
            f"Error processing {uploaded_file.name} after multiple attempts: {e}"
        )
        return {"Source File": uploaded_file.name}, full_text


# --- Multiple File Uploader ---
uploaded_files = st.file_uploader(
    "Upload your bill PDF(s)", type="pdf", accept_multiple_files=True
)

if uploaded_files:
  st.success(f"Successfully loaded **{len(uploaded_files)}** bill file(s).")

  # Check API Key validity before processing
  active_key = api_key_input.strip() or os.environ.get("GEMINI_API_KEY")

  if st.button("🚀 Process Bills with AI"):
    if not active_key:
      st.error(
          "⚠️ Please provide your Gemini API Key in the sidebar or set your"
          " GEMINI_API_KEY environment variable."
      )
    else:
      all_rows = []
      raw_texts = {}

      progress_bar = st.progress(0)
      status_text = st.empty()

      for idx, uploaded_file in enumerate(uploaded_files):
        status_text.text(
            f"Analyzing bill {idx + 1} of {len(uploaded_files)} with AI:"
            f" {uploaded_file.name}"
        )
        row_data, full_text = parse_bill_with_gemini(uploaded_file, active_key)
        all_rows.append(row_data)
        raw_texts[uploaded_file.name] = full_text
        progress_bar.progress((idx + 1) / len(uploaded_files))

      status_text.text("Extraction completed successfully!")

      # Master DataFrame (1 Row per Bill PDF)
      df = pd.DataFrame(all_rows)

      # Reorder columns to put 'Source File' first if present
      if "Source File" in df.columns:
        cols = ["Source File"] + [c for c in df.columns if c != "Source File"]
        df = df[cols]

      st.markdown("---")
      st.subheader("📊 Structured Bill Summary (1 Row per Bill)")
      st.dataframe(df, use_container_width=True)

      # Excel Export
      output = BytesIO()
      with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Bill Summary")
      excel_data = output.getvalue()

      st.markdown("---")
      col1, col2 = st.columns([2, 1])
      with col1:
        st.markdown(
            "Your structured master Excel sheet is ready for download."
        )
      with col2:
        st.download_button(
            label="📥 Download Master Excel File",
            data=excel_data,
            file_name="electricity_bills_ai_structured.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

      # Raw Text Inspection Expander
      with st.expander(
          "🔍 View Raw Text of Processed Bills (For Layout Verification)"
      ):
        for fname, text in raw_texts.items():
          st.markdown(f"**File: {fname}**")
          st.text(text[:2000] + "\n... [truncated]")
