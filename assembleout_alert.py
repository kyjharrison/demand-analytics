"""
Checks the ASSEMBLEOUT bin for any inventory that's been sitting for more than 2 days. 
If any found, emails a list to the inventory team. 
Otherwise, emails me a confirmation of nothing found. 
"""

import sqlite3
import pandas as pd
from pathlib import Path
import win32com.client
import json

with open(Path(__file__).parent.parent / "internal/config.json") as f:
    config = json.load(f)

CONN_RAW = sqlite3.connect(config["DB_RAW"])
CUTOFF = (pd.Timestamp.now() - pd.offsets.BusinessDay(2)).strftime('%Y-%m-%d')

query = """
WITH running_balance AS(
	SELECT 
		Item_No,
		Registering_Date,
		SUM(Quantity) 
			OVER (PARTITION BY Item_No ORDER BY Registering_Date ASC)
			AS Balance,
		ROW_NUMBER() 
			OVER (PARTITION BY Item_No ORDER BY Registering_Date DESC) 
			AS rn 
		FROM Warehouse_Entries_Excel
	WHERE Bin_Code = 'ASSEMBLEOUT' 
),

last_emptied AS(
	SELECT Item_No, MAX(Registering_Date) as last_emptied_date FROM running_balance
	WHERE Balance = 0
	GROUP BY Item_No
)

SELECT 
	Item_No as Item,
	MAX(CASE WHEN rn = 1 THEN Balance END) as Qty,
	Min(Registering_Date) as 'Date Posted' 
	FROM running_balance
LEFT JOIN last_emptied USING (Item_No)
WHERE Balance > 0 
	AND Registering_Date > last_emptied_date
GROUP BY Item_No
HAVING Min(Registering_Date) < :CUTOFF
ORDER BY 'Date Posted'
"""

df = pd.read_sql(query, CONN_RAW, params={"CUTOFF": CUTOFF})

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
	This is an automated alert that the following inventory appears to have been in ASSEMBLEOUT for more than 2 days.<br><br>
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
	mail.Subject = "ASSEMBLEOUT clear EOM"
	mail.Send()