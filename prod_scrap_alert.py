"""
Emails inventory team a list of what's in the PRODUCTION SCRAP bin 
Runs weekly on Monday mornings
"""

import sqlite3
import pandas as pd
from pathlib import Path
import win32com.client
import json
from alert import send_alert

with open(Path(__file__).parent.parent / "internal/config.json") as f:
    config = json.load(f)

CONN_CLEAN = sqlite3.connect(config["DB_CLEAN"])

query = """
    SELECT * from bin_contents
    WHERE Bin_Code = "PRODUCTION SCRAP"
    """

try:
    df = pd.read_sql(query, CONN_CLEAN)
    if not df.empty:
        df['Qty'] = df['Qty'].apply(lambda x: f"{x:,}")
        table_html = df.to_html(index=False, border=0).replace(
            '<table',
            '<table style="border-collapse: collapse; font-family: Aptos, sans-serif; font-size: 16px;"'
        ).replace('<td', '<td style="padding: 2px 16px;text-align: right;"').replace('<th>', '<th style="padding: 2px 16px;text-align: right;">')
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = config["inventory_supervisor"]
        mail.CC = config["cc_me"]
        mail.Subject = "PRODUCTION SCRAP"
        mail.HTMLBody = f"""Good morning, <br><br>
        This is an automated alert that the following inventory is in PRODUCTION SCRAP.<br><br>
        {table_html} <br>
        Thank you,<br>
        {config["me"]}<br>
        {config["signature"]}
        """
        mail.Send()

    else:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = config["cc_me"]
        mail.Subject = "PROD SCRAP clear EOM"
        mail.Send()

except Exception as e:
    send_alert("PROD SCRAP ERROR", e)

