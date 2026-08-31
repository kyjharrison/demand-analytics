"""
Checks the ASSEMBLEOUT bin for any inventory that's been sitting for more than 2 days. 
If any found, emails a list to the inventory team. 
Otherwise, emails me a confirmation of nothing found. 
"""

import json
import pandas as pd
import sqlite3
import sys
import win32com.client

from datetime import datetime
from pathlib import Path

from error_alert import send_alert

# exit if outside business hours
now = datetime.now()
if now.weekday() >= 5 or not (6 <= now.hour < 20):
    sys.exit(0)

try:
	with open(Path(__file__).parent.parent / "config.json") as f:
		config = json.load(f)

	CONN = sqlite3.connect(Path(config["MIRROR_DIR"]) / "clean_mirror.db")
	CUTOFF = (pd.Timestamp.now() - pd.offsets.BusinessDay(2)).strftime('%Y-%m-%d')

	query = (Path(__file__).parent / "assembleout_alert.sql").read_text()

	df = pd.read_sql(query, CONN, params={"CUTOFF": CUTOFF})

	if not df.empty:

		df['Qty'] = df['Qty'].apply(lambda x: f"{x:,}")
		table_html = df.to_html(index=False, border=0).replace(
			'<table',
			'<table style="border-collapse: collapse; font-family: Aptos, sans-serif; font-size: 16px;"'
		).replace('<td', '<td style="padding: 2px 16px;text-align: right;"').replace('<th>', '<th style="padding: 2px 16px;text-align: right;">')

		outlook = win32com.client.Dispatch("Outlook.Application")
		mail = outlook.CreateItem(0)
		mail.To = config["inventory_team"]
		mail.CC = f"{config["production_manager"]}; {config["cc_me"]}"
		mail.Subject = "ASSEMBLEOUT"
		mail.HTMLBody = f"""Good morning, <br><br>
		Please check on these items as they have been in ASSEMBLEOUT for more than 2 days.<br><br>
		{table_html} <br>
		Thank you,<br>
		{config["name"]}<br>
		{config["title"]}
		"""

		mail.Send()

	else:
		outlook = win32com.client.Dispatch("Outlook.Application")
		mail = outlook.CreateItem(0)
		mail.To = config["cc_me"]
		mail.Subject = "ASSEMBLEOUT clear EOM"
		mail.Send()

except Exception as e:
	send_alert("ASSEMBLEOUT ERROR", e)