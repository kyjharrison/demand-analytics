SELECT sl.Document_No, sl.Line_No, sl.Sell_to_Customer_No, sl.No, sl.Description, sl.Location_Code, sl.Shortcut_Dimension_1_Code, sl.Shipment_Date, sl.Outstanding_Quantity, 
	sku.Inventory AS 'Qty on Hand 02'
FROM Sales_Lines_Excel sl
LEFT JOIN Stockkeeping_Unit_Card_Excel sku
	ON sl.No = sku.Item_No
	AND sku.Location_Code = '02'
WHERE sl.Location_Code = '02'
	AND sl.Outstanding_Quantity > 0
	AND Type = 'Item'
	AND No != '99998'
	AND sl.No NOT LIKE 'CN466%'
	AND Document_Type = 'Order'
	AND (
		sku.Item_No is NULL
		OR sku.inventory < sl.Outstanding_Quantity
	)
	