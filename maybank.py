import regex as re

# ============================================================
# YEAR DETECTION
# ============================================================

STATEMENT_YEAR_PATTERN = re.compile(
    r"STATEMENT\s+DATE\s*:?\s*\d{2}/\d{2}/(\d{2,4})",
    re.IGNORECASE
)

# 🔑 module-level cache (persists across pages)
_CACHED_STATEMENT_YEAR = None


def extract_statement_year(text, fallback_year):
    global _CACHED_STATEMENT_YEAR

    # If already detected earlier, reuse it
    if _CACHED_STATEMENT_YEAR:
        return _CACHED_STATEMENT_YEAR

    m = STATEMENT_YEAR_PATTERN.search(text)
    if not m:
        return fallback_year

    y = m.group(1)
    if len(y) == 2:
        year = f"20{y}"
    else:
        year = y

    _CACHED_STATEMENT_YEAR = year
    return year


# ============================================================
# MTASB FORMAT
# ============================================================

PATTERN_MAYBANK_MTASB = re.compile(
    r"(\d{2}/\d{2})\s+"
    r"(.+?)\s+"
    r"([0-9,]+\.\d{2})([+-])\s+"
    r"([0-9,]+\.\d{2})"
)


def parse_line_maybank_mtasb(line, page_num, year):
    m = PATTERN_MAYBANK_MTASB.search(line)
    if not m:
        return None

    date_raw, desc, amount_raw, sign, balance_raw = m.groups()
    day, month = date_raw.split("/")

    amount = float(amount_raw.replace(",", ""))
    balance = float(balance_raw.replace(",", ""))

    return {
        "date": f"{year}-{month}-{day}",
        "description": desc.strip(),
        "debit": amount if sign == "-" else 0.0,
        "credit": amount if sign == "+" else 0.0,
        "balance": balance,
        "page": page_num,
    }


# ============================================================
# MBB FORMAT
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

    day, mon, year, desc, amount_raw, sign, balance_raw = m.groups()
    month = MONTH_MAP.get(mon.title(), "01")

    amount = float(amount_raw.replace(",", ""))
    balance = float(balance_raw.replace(",", ""))

    return {
        "date": f"{year}-{month}-{day}",
        "description": desc.strip(),
        "debit": amount if sign == "-" else 0.0,
        "credit": amount if sign == "+" else 0.0,
        "balance": balance,
        "page": page_num,
    }


# ============================================================
# MAIN ENTRY (NO app.py CHANGES NEEDED)
# ============================================================

def parse_transactions_maybank(text, page_num, default_year="2025"):
    tx_list = []

    year = extract_statement_year(text, default_year)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        tx = parse_line_maybank_mtasb(line, page_num, year)
        if tx:
            tx_list.append(tx)
            continue

        tx = parse_line_maybank_mbb(line, page_num)
        if tx:
            tx_list.append(tx)
            continue

    return tx_list
