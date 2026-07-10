SELECT sl.Document_No, sl.Line_No, sl.Sell_to_Customer_No, sl.No, sl.Description, sl.Location_Code, sl.Shortcut_Dimension_1_Code, sl.Shipment_Date, sl.Outstanding_Quantity, 
	sku02.Inventory AS 'Qty on Hand 02',
	sku01.Inventory AS 'Qty on Hand 01'
FROM Sales_Lines_Excel sl
LEFT JOIN Stockkeeping_Unit_Card_Excel sku02
	ON sl.No = sku02.Item_No
	AND sku02.Location_Code = '02'
LEFT JOIN Stockkeeping_Unit_Card_Excel sku01
	ON sl.No = sku01.Item_No
	AND sku01.Location_Code = '01'
WHERE sl.Location_Code = '02'
	AND sl.Outstanding_Quantity > 0
	AND sl.Type = 'Item'
	AND sl.No != '99998'
	AND sl.No NOT LIKE 'CN466%'
	AND Document_Type = 'Order'
	AND (
		sku02.Item_No is NULL
		OR sku02.inventory < sl.Outstanding_Quantity
	)
ORDER BY Document_No
	