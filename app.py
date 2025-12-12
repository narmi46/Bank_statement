import streamlit as st
import pdfplumber
import json
import pandas as pd
from datetime import datetime

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
# Bank Selection
# ---------------------------------------------------

bank_choice = st.selectbox(
    "Select Bank Format",
    ["Auto-detect", "Maybank", "Public Bank (PBB)", "RHB Bank", "CIMB Bank"]
)

bank_hint = None
if bank_choice == "Maybank":
    bank_hint = "maybank"
elif bank_choice == "Public Bank (PBB)":
    bank_hint = "pbb"
elif bank_choice == "RHB Bank":
    bank_hint = "rhb"
elif bank_choice == "CIMB Bank":
    bank_hint = "cimb"

# ---------------------------------------------------
# File Upload
# ---------------------------------------------------

uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# ---------------------------------------------------
# Auto Detect Parsing Logic
# ---------------------------------------------------

def auto_detect_and_parse(text, page_obj, page_num, **source_file_kwargs):
    """
    Tries all parsers. 
    """
    source_file = source_file_kwargs.get("source_file", "AutoDetect")

    # CIMB parser
    if "CIMB" in text or "cimb" in text.lower():
        tx = parse_transactions_cimb(page_obj, page_num, source_file)
        if tx: return tx

    # Maybank
    tx = parse_transactions_maybank(text, page_num)
    if tx: return tx

    # Public Bank
    tx = parse_transactions_pbb(text, page_num)
    if tx: return tx

    # RHB
    tx = parse_transactions_rhb(text, page_num)
    if tx: return tx

    return []

# ---------------------------------------------------
# Helper function to infer year from dates
# ---------------------------------------------------

def infer_and_fix_years(transactions):
    """
    Infers the correct year for transactions based on chronological order.
    Assumes dates without year or with ambiguous years should follow logical sequence.
    """
    if not transactions:
        return transactions
    
    current_year = datetime.now().year
    prev_month = None
    assigned_year = current_year
    
    for tx in transactions:
        date_str = tx.get("date", "")
        
        # Try to parse the date
        try:
            # Handle various date formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d/%m", "%d-%m"]:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    
                    # If year is not in format, assign based on sequence
                    if fmt in ["%d/%m", "%d-%m"]:
                        month = parsed_date.month
                        
                        # Detect year rollback (e.g., Dec -> Jan means new year)
                        if prev_month and month < prev_month and prev_month >= 11 and month <= 2:
                            assigned_year += 1
                        
                        parsed_date = parsed_date.replace(year=assigned_year)
                        prev_month = month
                    else:
                        # Use the year from the date
                        assigned_year = parsed_date.year
                        prev_month = parsed_date.month
                    
                    # Update transaction with full date
                    tx["date"] = parsed_date.strftime("%d/%m/%Y")
                    break
                except ValueError:
                    continue
        except:
            pass
    
    return transactions

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
                        tx = parse_transactions_maybank(text, page_num)

                    elif bank_hint == "pbb":
                        tx = parse_transactions_pbb(text, page_num)

                    elif bank_hint == "rhb":
                        tx = parse_transactions_rhb(text, page_num)

                    elif bank_hint == "cimb":
                        tx = parse_transactions_cimb(page, page_num, uploaded_file.name)

                    else:
                        tx = auto_detect_and_parse(
                            text=text,
                            page_obj=page,
                            page_num=page_num,
                            source_file=uploaded_file.name
                        )

                    if tx:
                        for t in tx:
                            t["source_file"] = uploaded_file.name
                        all_tx.extend(tx)

        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

    # Fix years after all transactions are collected
    all_tx = infer_and_fix_years(all_tx)

# ---------------------------------------------------
# ASCII TABLE EXPORT FUNCTION
# ---------------------------------------------------

def dataframe_to_ascii(df):
    # Convert all cells to strings
    df_str = df.astype(str)

    # Compute column widths
    col_widths = {col: max(df_str[col].map(len).max(), len(col)) for col in df_str.columns}

    # Build horizontal separator
    separator = "+".join("-" * (col_widths[col] + 2) for col in df_str.columns)
    separator = "+" + separator + "+"

    # Build header row
    header = "|" + "|".join(f" {col.ljust(col_widths[col])} " for col in df_str.columns) + "|"

    # Build data rows
    rows = [
        "|" + "|".join(f" {str(val).ljust(col_widths[col])} " for col, val in row.items()) + "|"
        for _, row in df_str.iterrows()
    ]

    # Join all parts
    table = "\n".join([separator, header, separator] + rows + [separator])
    return table


# ---------------------------------------------------
# Display Results
# ---------------------------------------------------

if all_tx:
    st.subheader("Extracted Transactions")

    df = pd.DataFrame(all_tx)

    # Enforce column order if exists
    cols = ["date", "description", "debit", "credit", "balance", "page", "source_file"]
    df = df[[c for c in cols if c in df.columns]]

    st.dataframe(df, use_container_width=True)

    # ---------------------------------------------------
    # Monthly Statistics
    # ---------------------------------------------------
    
    st.subheader("Monthly Statistics")
    
    # Convert date column to datetime for grouping
    df['date_parsed'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    df['year_month'] = df['date_parsed'].dt.to_period('M')
    
    # Convert debit, credit, balance to numeric
    df['debit_num'] = pd.to_numeric(df['debit'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['credit_num'] = pd.to_numeric(df['credit'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['balance_num'] = pd.to_numeric(df['balance'].astype(str).str.replace(',', ''), errors='coerce')
    
    # Group by month
    monthly_stats = df.groupby('year_month').agg({
        'debit_num': 'sum',
        'credit_num': 'sum',
        'balance_num': ['min', 'max']
    }).reset_index()
    
    # Flatten column names
    monthly_stats.columns = ['Month', 'Total Debit', 'Total Credit', 'Lowest Balance', 'Highest Balance']
    
    # Format numbers with commas
    monthly_stats['Total Debit'] = monthly_stats['Total Debit'].apply(lambda x: f"{x:,.2f}")
    monthly_stats['Total Credit'] = monthly_stats['Total Credit'].apply(lambda x: f"{x:,.2f}")
    monthly_stats['Lowest Balance'] = monthly_stats['Lowest Balance'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A")
    monthly_stats['Highest Balance'] = monthly_stats['Highest Balance'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A")
    
    st.dataframe(monthly_stats, use_container_width=True)

    # JSON Download
    json_data = json.dumps(df[cols].to_dict(orient="records"), indent=4)
    st.download_button("Download JSON", json_data, file_name="transactions.json", mime="application/json")

    # TXT (ASCII TABLE) Download
    ascii_txt = dataframe_to_ascii(df[cols])

    st.download_button(
        "Download TXT (ASCII Table)",
        ascii_txt,
        file_name="transactions.txt",
        mime="text/plain"
    )

else:
    if uploaded_files:
        st.warning("No transactions found. Check if the file format is supported.")
