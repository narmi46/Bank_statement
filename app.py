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
# Default Year
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
# Display Results & Monthly Summary
# ---------------------------------------------------

if all_tx:
    st.subheader("📋 Extracted Transactions")

    df = pd.DataFrame(all_tx)

    # Enforce column order
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

    # -----------------------------------------------
    # Normalize data types
    # -----------------------------------------------

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["debit", "credit", "balance"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("", "0")
                .astype(float)
            )

    st.dataframe(df, use_container_width=True)

    # -----------------------------------------------
    # Monthly Summary
    # -----------------------------------------------

    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly_summary = (
        df.groupby("month")
        .agg(
            total_debit=("debit", "sum"),
            total_credit=("credit", "sum"),
            ending_balance=("balance", "last"),
            lowest_balance=("balance", "min"),
            highest_balance=("balance", "max"),
            transaction_count=("date", "count"),
            source_files=("source_file", lambda x: ", ".join(sorted(set(x))))
        )
        .reset_index()
        .sort_values("month")
    )

    st.subheader("📊 Monthly Summary")
    st.dataframe(monthly_summary, use_container_width=True)

    # -----------------------------------------------
    # Downloads
    # -----------------------------------------------

    # JSON
    json_data = json.dumps(df.to_dict(orient="records"), indent=4)
    st.download_button(
        "Download JSON",
        json_data,
        file_name="transactions.json",
        mime="application/json"
    )

    # Excel (2 sheets)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Transactions"
        )
        monthly_summary.to_excel(
            writer,
            index=False,
            sheet_name="Monthly Summary"
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
