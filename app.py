import streamlit as st
import pdfplumber
import json
import pandas as pd
from io import BytesIO

# ---------------------------------------------------
# Import parsers
# ---------------------------------------------------

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
# Default Year (RESTORED)
# ---------------------------------------------------

default_year = st.text_input(
    "Default Year (used if statement has no year)",
    value="2025"
)

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

                    text = page.extract_text() or ""
                    tx = []

                    if bank_hint == "maybank":
                        tx = parse_transactions_maybank(
                            text,
                            page_num,
                            default_year
                        )

                    elif bank_hint == "pbb":
                        tx = parse_transactions_pbb(
                            text,
                            page_num,
                            default_year
                        )

                    elif bank_hint == "rhb":
                        tx = parse_transactions_rhb(
                            text,
                            page_num
                        )

                    elif bank_hint == "cimb":
                        tx = parse_transactions_cimb(
                            page,
                            page_num,
                            uploaded_file.name
                        )

                    if tx:
                        for t in tx:
                            t["source_file"] = uploaded_file.name
                        all_tx.extend(tx)

        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

# ---------------------------------------------------
# Display Results & Downloads
# ---------------------------------------------------

if all_tx:
    st.subheader("Extracted Transactions")

    df = pd.DataFrame(all_tx)

    columns = [
        "date",
        "description",
        "debit",
        "credit",
        "balance",
        "page",
        "source_file"
    ]
    df = df[[c for c in columns if c in df.columns]]

    st.dataframe(df, use_container_width=True)

    # ----------------------------
    # JSON Download
    # ----------------------------

    json_data = json.dumps(df.to_dict(orient="records"), indent=4)
    st.download_button(
        "Download JSON",
        json_data,
        file_name="transactions.json",
        mime="application/json"
    )

    # ----------------------------
    # Excel Download (.xlsx)
    # ----------------------------

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Transactions"
        )

    st.download_button(
        "Download Excel (.xlsx)",
        output.getvalue(),
        file_name="transactions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    if uploaded_files:
        st.warning(
            "No transactions found. Make sure the correct bank format is selected."
        )
