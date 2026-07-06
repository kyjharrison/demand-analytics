WITH running_balance AS(
	SELECT Entry_No, Entry_Type, Journal_Batch_Name, Line_No, Location_Code, Bin_Code, Item_No,  Whse_Document_Type, Whse_Document_No, Registering_Date, User_ID,
		SUM(Quantity) 
			OVER (PARTITION BY Item_No ORDER BY Registering_Date ASC)
			AS Balance,
		ROW_NUMBER() 
			OVER (PARTITION BY Item_No ORDER BY Registering_Date DESC) 
			AS rn 
		FROM Warehouse_Entries_Excel
	WHERE Bin_Code = 'ASSEMBLEOUT' 
	ORDER BY Registering_Date DESC
)

SELECT Item_No, Balance, Registering_Date FROM running_balance
WHERE rn = 1 AND Balance > 0 
ORDER BY Registering_Date