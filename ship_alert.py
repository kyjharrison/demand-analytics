"""
Checks the SHIP bin for any inventory that's been sitting for more than 2 days. 
If any found, emails a list to the shipping manager
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
	WHERE Bin_Code = 'SHIP' 
),

last_emptied AS(
	SELECT Item_No, MAX(Registering_Date) as last_emptied_date FROM running_balance
	WHERE Balance = 0
	GROUP BY Item_No
)

SELECT 
	Item_No as Item,
	Min(Registering_Date) as 'Date Posted',
	MAX(CASE WHEN rn = 1 THEN Balance END) as Qty
	FROM running_balance
LEFT JOIN last_emptied USING (Item_No)
WHERE Balance > 0 
	AND Registering_Date > last_emptied_date
GROUP BY Item_No
HAVING Min(Registering_Date) < :CUTOFF
    AND MAX(CASE WHEN rn = 1 THEN Balance END) > 0
ORDER BY Min(Registering_Date) ASC
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
	mail.To = config["david"]
	mail.CC = config["cc_me"]
	mail.Subject = "SHIP"
	mail.HTMLBody = f"""Hey David, <br><br>
	Here's a test load of what the SHIP bin query is returning. The dates are the original dates it went out of alignment<br><br>
	{table_html} <br>
	Thank you,<br>
	{config["me"]}<br>
	{config["signature"]}
	"""

	mail.Display()

else:
	outlook = win32com.client.Dispatch("Outlook.Application")
	mail = outlook.CreateItem(0)
	mail.To = config["cc_me"]
	mail.Subject = "SHIP clear EOM"
	mail.Send()