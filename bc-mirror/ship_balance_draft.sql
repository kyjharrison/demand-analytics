WITH daily_balance AS(
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
	SELECT Item_No, MAX(Registering_Date) as last_emptied_date FROM daily_balance
	WHERE Balance = 0
	GROUP BY Item_No
),

originating_entry AS(
	SELECT
		bal.Item_No,
		we.Source_No,
		ROW_NUMBER() OVER (PARTITION BY bal.Item_No ORDER BY we.Entry_No ASC) AS rn
	FROM daily_balance bal
	LEFT JOIN last_emptied le USING (Item_No)
	JOIN Warehouse_Entries_Excel we
		ON we.Item_No = bal.Item_No
		AND we.Registering_Date = bal.Registering_Date
		AND we.Bin_Code = 'SHIP'
	WHERE bal.Balance > 0
		AND (le.last_emptied_date IS NULL OR bal.Registering_Date > le.last_emptied_date)
)

SELECT 
	bal.Item_No as Item,
	MAX(CASE WHEN bal.rn = 1 THEN bal.Balance END) as Qty,
	Min(bal.Registering_Date) as 'Date Posted' ,
	sl.Sell_to_Customer_No AS Customer
FROM daily_balance bal	
LEFT JOIN last_emptied USING (Item_No)
LEFT JOIN originating_entry oe USING (Item_No)
LEFT JOIN Sales_Lines_Excel sl ON sl.Document_No = oe.Source_No
WHERE bal.Balance > 0 
	AND (last_emptied_date IS NULL OR bal.Registering_Date > last_emptied_date)
GROUP BY bal.Item_No
HAVING Min(bal.Registering_Date) < DATE('now', '-2 days')
	AND MAX(CASE WHEN bal.rn = 1 THEN bal.Balance END) > 0
ORDER BY Min(bal.Registering_Date) ASC