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
HAVING Min(Registering_Date) < DATE('now', '-2 days')