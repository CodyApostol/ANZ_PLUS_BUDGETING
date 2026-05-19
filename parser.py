import pandas as pd
import re
from datetime import datetime

VALID_MONTHS = {"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"}

def parse_statement(text: str) -> pd.DataFrame:
    """Parse a bank statement from a raw text string (not a file path)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    transactions = []
    i = 0

    while i < len(lines):
        line = lines[i]
        parts = line.split()

        if len(parts) >= 2:
            day_candidate = parts[0]
            month_candidate = parts[1]

            if day_candidate.isdigit() and month_candidate in VALID_MONTHS:
                try:
                    day = int(day_candidate)
                    month = month_candidate

                    # Infer year from the month string in the text if possible,
                    # otherwise default to the current year
                    year = _infer_year(lines, month)

                    date = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")

                    # Extract amounts
                    amounts = re.findall(r'\$[\d,]+\.\d{2}', line)
                    if len(amounts) >= 1:
                        amount1 = float(amounts[-2].replace('$', '').replace(',', ''))

                        # Remove amounts and date from line to get description
                        line_clean = line
                        for amt in amounts[-1:]:
                            line_clean = line_clean.replace(amt, '').strip()
                        desc = re.sub(r'^\d{1,2} \w{3}', '', line_clean).strip()

                        # Append next line if not Effective Date (likely address)
                        if i + 1 < len(lines) and not lines[i + 1].lower().startswith("effective date"):
                            desc += " | " + lines[i + 1].strip()
                            i += 1

                        # Skip transfers and rounding
                        if re.search(r"TRANSFER FROM|TRANSFER TO|ROUND UP", desc, re.IGNORECASE):
                            i += 1
                            continue

                        # Cleaning description
                        desc = re.sub(r"^.*?\b\d{4}\b\s*", "", desc)
                        desc = re.sub(r"\$\d+(?:\.\d{2})?", "", desc)
                        desc = re.sub(r"\s*\d+\.\d{2}$", "", desc)
                        desc = re.sub(r"/.*", "", desc)
                        desc = desc.strip().rstrip('|').strip()

                        # Split into store and suburb if available
                        if "|" in desc:
                            store, _ = [part.strip() for part in desc.split("|", 1)]
                        else:
                            store = desc

                        # Remove only standalone numbers, keep numbers inside words like 7-ELEVEN
                        store = re.sub(r'(?<=\s)\d+(?=\s)|^\d+(?=\s)|(?<=\s)\d+$', '', store).strip()

                        if store.upper() == "DEPARTMENT OF":
                            store = "DEPARTMENT OF TRANSPORT"

                        transactions.append({
                            "Date": date,
                            "Store": store,
                            "Spending": amount1
                        })

                except Exception as e:
                    pass  # silently skip unparseable lines in UI context

        i += 1

    return pd.DataFrame(transactions)


def _infer_year(lines: list, month: str) -> str:
    """Try to find a 4-digit year in the statement header lines, else use current year."""
    from datetime import date
    for line in lines[:20]:  # year usually appears near the top of the statement
        match = re.search(r'\b(20\d{2})\b', line)
        if match:
            return match.group(1)
    return str(date.today().year)
