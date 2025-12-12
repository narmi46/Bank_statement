import streamlit as st
import pdfplumber
import json
import pandas as pd

# Import parsers
from maybank import parse_transactions_maybank
from public_bank import parse_transactions_pbb
from rhb import parse_transactions_rhb
from cimb import parse_transactions_cimb

# ---------------------------------------------------
# Streamlit Setup
# ---------------------------------------------------

st.set_page_config(page_title="Bank Statement Parser", layout="wide")
st.title("📄 Bank Statement Parser (Multi-File Support)")
st.write("Upload one or more bank statement PDFs to extract transactions.")

# ---------------------------------------------------
# Config
# ---------------------------------------------------

DEFAULT_YEAR = "2025"  # <-- change here if needed

# ---------------------------------------------------
# Bank Selection (NO AUTO-DETECT)
# ---------------------------------------------------

bank_choice = st.selectbox(
    "Select Bank Format",
    ["Maybank", "Public Bank (PBB)", "RHB Bank", "CIMB Bank"]
)

bank_hint = {
    "Maybank": "maybank",
    "Public Bank (PBB)": "pbb",
    "RHB Bank": "rhb",
    "CIMB Bank": "cimb",
}[bank_choice]

# ---------------------------------------------------
# File Upload
# ---------------------------------------------------

uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

# ---------------------------------------------------
# Main Processing
# ---------------------------------------------------

all_tx = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write(f"Processing: **{uploaded_file.name}**")

        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):

                    text = page.extract_text() or []
                    tx = []

                    if bank_hint == "maybank":
                        tx = parse_transactions_maybank(text, page_num, DEFAULT_YEAR)

                    elif bank_hint == "pbb":
                        tx = parse_transactions_pbb(text, page_num, DEFAULT_YEAR)

                    elif bank_hint == "rhb":
                        tx = parse_transactions_rhb(text, page_num)

                    elif bank_hint == "cimb":
                        tx = parse_transactions_cimb(page, page_num, uploaded_file.name)

                    if tx:
                        for t in tx:
                            t["source_file"] = uploaded_file.name
                        all_tx.extend(tx)

        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

# ---------------------------------------------------
# ASCII TABLE EXPORT FUNCTION
# ---------------------------------------------------

def dataframe_to_ascii(df):
    df_str = df.astype(str)

    col_widths = {
        col: max(df_str[col].map(len).max(), len(col))
        for col in df_str.columns
    }

    separator = "+" + "+".join("-" * (col_widths[col] + 2) for col in df_str.columns) + "+"

    header = "|" + "|".join(
        f" {col.ljust(col_widths[col])} " for col in df_str.columns
    ) + "|"

    rows = [
        "|" + "|".join(
            f" {str(val).ljust(col_widths[col])} "
            for col, val in row.items()
        ) + "|"
        for _, row in df_str.iterrows()
    ]

    return "\n".join([separator, header, separator] + rows + [separator])

# ---------------------------------------------------
# Display Results
# ---------------------------------------------------

if all_tx:
    st.subheader("Extracted Transactions")

    df = pd.DataFrame(all_tx)

    cols = ["date", "description", "debit", "credit", "balance", "page", "source_file"]
    df = df[[c for c in cols if c in df.columns]]

    st.dataframe(df, use_container_width=True)

    # JSON Download
    json_data = json.dumps(df.to_dict(orient="records"), indent=4)
    st.download_button(
        "Download JSON",
        json_data,
        file_name="transactions.json",
        mime="application/json"
    )

    # TXT Download
    ascii_txt = dataframe_to_ascii(df)
    st.download_button(
        "Download TXT (ASCII Table)",
        ascii_txt,
        file_name="transactions.txt",
        mime="text/plain"
    )

else:
    if uploaded_files:
        st.warning("No transactions found. Check if the correct bank format is selected.")
