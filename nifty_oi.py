import requests
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================
# GOOGLE SHEET SETTINGS
# ==========================

SPREADSHEET_ID = "1DDivMNeKciGzPIJZdVnM98q7Roo3UkhvGpGJvxrw2XQ"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json",
    scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key(
    SPREADSHEET_ID
).worksheet("TrendingOI")

# ==========================
# NSE SESSION
# ==========================

session = requests.Session()

session.get(
    "https://www.nseindia.com",
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nseindia.com/option-chain",
    "Accept": "application/json,text/plain,*/*"
}

# ==========================
# NSE OPTION CHAIN API
# CHANGE EXPIRY WHEN NEEDED
# ==========================

r = session.get(
    "https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=NIFTY&expiry=30-Jun-2026",
    headers=headers,
    timeout=30
)

data = json.loads(
    r.text.encode().decode("utf-8-sig")
)

# ==========================
# SPOT & ATM
# ==========================

spot = data["records"]["data"][0]["CE"]["underlyingValue"]

atm = round(spot / 50) * 50

# ==========================
# ATM ± 7 STRIKES
# ==========================

strikes = [
    atm + (i * 50)
    for i in range(-7, 8)
]

# ==========================
# OI CALCULATION
# ==========================

call_oi = 0
put_oi = 0

for row in data["records"]["data"]:

    strike = row.get("strikePrice")

    if strike in strikes:

        if "CE" in row:
            call_oi += row["CE"].get(
                "changeinOpenInterest",
                0
            )

        if "PE" in row:
            put_oi += row["PE"].get(
                "changeinOpenInterest",
                0
            )

# ==========================
# TRENDING OI LOGIC
# ==========================

diff_oi = put_oi - call_oi

direction = "Bullish" if diff_oi > 0 else "Bearish"

pcr = round(
    abs(put_oi) / abs(call_oi),
    2
) if call_oi != 0 else 0

sentiment = "Neutral"

if pcr > 1 and diff_oi > 0:
    sentiment = "Bullish"

elif pcr < 1 and diff_oi < 0:
    sentiment = "Bearish"

# ==========================
# PREVIOUS ROW COMPARISON
# ==========================

last_row = len(sheet.get_all_values())

direction_change = ""
direction_percent = ""

if last_row > 1:

    prev_diff = sheet.cell(
        last_row,
        7
    ).value

    try:

        prev_diff = float(prev_diff)

        direction_change = (
            diff_oi - prev_diff
        )

        if prev_diff != 0:

            direction_percent = round(
                (
                    direction_change
                    / abs(prev_diff)
                ) * 100,
                2
            )

    except:
        pass

# ==========================
# WRITE TO GOOGLE SHEET
# ==========================

now = datetime.now()

sheet.append_row([

    now.strftime("%d-%m-%Y"),      # Date
    now.strftime("%H:%M:%S"),      # Time

    round(spot, 2),               # LTP
    atm,                          # ATM

    round(call_oi, 2),            # Call OI Chg
    round(put_oi, 2),             # Put OI Chg

    round(diff_oi, 2),            # Diff OI

    direction,                    # Direction

    round(direction_change, 2)
    if direction_change != ""
    else "",

    direction_percent,

    pcr,

    sentiment

])

# ==========================
# CONSOLE OUTPUT
# ==========================

print("Data Added Successfully")
print("Spot:", spot)
print("ATM:", atm)
print("Call OI:", call_oi)
print("Put OI:", put_oi)
print("Diff OI:", diff_oi)
print("Direction:", direction)
print("Direction Change:", direction_change)
print("Direction %:", direction_percent)
print("PCR:", pcr)
print("Sentiment:", sentiment)