import regex as re

# ============================================================
# YEAR DETECTION (FROM STATEMENT HEADER)
# Example: "STATEMENT DATE : 30/06/25"
# ============================================================

STATEMENT_YEAR_PATTERN = re.compile(
    r"STATEMENT DATE\s*:\s*\d{2}/\d{2}/(\d{2})"
)

def extract_statement_year(text, fallback_year):
    """
    Extracts year from statement header.
    Falls back to DEFAULT_YEAR if not found.
    """
    m = STATEMENT_YEAR_PATTERN.search(text)
    if not m:
        return fallback_year

    yy = int(m.group(1))
    return f"20{yy:02d}"


# ============================================================
# MTASB Pattern (Maybank Variant)
# Example:
# "01/06 TRANSFER TO A/C 5,000.00+ 9,318.33"
# ============================================================

PATTERN_MAYBANK_MTASB = re.compile(
    r"(\d{2}/\d{2})\s+"             # 01/06
    r"(.+?)\s+"                     # description
    r"([0-9,]+\.\d{2})([+-])\s+"    # amount + or -
    r"([0-9,]+\.\d{2})"             # balance
)

def parse_line_maybank_mtasb(line, page_num, year):
    m = PATTERN_MAYBANK_MTASB.search(line)
    if not m:
        return None

    date_raw, desc, amount_raw, sign, balance_raw = m.groups()
    day, month = date_raw.split("/")

    amount = float(amount_raw.replace(",", ""))
    balance = float(balance_raw.replace(",", ""))

    credit = amount if sign == "+" else 0.0
    debit  = amount if sign == "-" else 0.0

    full_date = f"{year}-{month}-{day}"

    return {
        "date": full_date,
        "description": desc.strip(),
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "page": page_num,
    }


# ============================================================
# MBB Pattern (Maybank Business Banking)
# Example:
# "01 Apr 2025 CMS - DR CORP CHG 78.00 - 71,229.76"
# ============================================================

PATTERN_MAYBANK_MBB = re.compile(
    r"(\d{2})\s+([A-Za-z]{3})\s+(\d{4})\s+"
    r"(.+?)\s+"
    r"([0-9,]+\.\d{2})\s+([+-])\s+"
    r"([0-9,]+\.\d{2})"
)

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
}

def parse_line_maybank_mbb(line, page_num):
    m = PATTERN_MAYBANK_MBB.search(line)
    if not m:
        return None

    day, mon_abbr, year, desc, amount_raw, sign, balance_raw = m.groups()
    month = MONTH_MAP.get(mon_abbr.title(), "01")

    amount = float(amount_raw.replace(",", ""))
    balance = float(balance_raw.replace(",", ""))

    credit = amount if sign == "+" else 0.0
    debit  = amount if sign == "-" else 0.0

    full_date = f"{year}-{month}-{day}"

    return {
        "date": full_date,
        "description": desc.strip(),
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "page": page_num,
    }


# ============================================================
# MAIN ENTRY (COMPATIBLE WITH app.py)
# ============================================================

def parse_transactions_maybank(text, page_num, default_year="2025"):
    """
    Parses both MTASB and MBB Maybank formats.
    Fully compatible with existing app.py
    """

    tx_list = []

    # 🔑 Auto-detect year ONCE per page
    year = extract_statement_year(text, default_year)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # MTASB
        tx = parse_line_maybank_mtasb(line, page_num, year)
        if tx:
            tx_list.append(tx)
            continue

        # MBB
        tx = parse_line_maybank_mbb(line, page_num)
        if tx:
            tx_list.append(tx)
            continue

    return tx_list
