SELECT 
	sku2.Item_No as Item,
	sku2.Description, 
	sku2.CGWShortcutDimension4Code as LC,
	sku2.Shelf_No, 
	sku2.Inventory as QtyOH02,
	(sku1.Inventory - sku1.Qty_on_Sales_Order) AS QtyAvail01,
	COALESCE(tr.InTransit, 0) AS InTransit,
	COALESCE(tr.Planned, 0) AS Planned
FROM Stockkeeping_Unit_Card_Excel sku2
LEFT JOIN Stockkeeping_Unit_Card_Excel sku1
	ON sku1.Item_No = sku2.Item_No
	AND sku1.Location_Code = '01'
	
LEFT JOIN (
	SELECT 
		ItemNo, 
		SUM(TransferOrderShippedQty) AS InTransit, 
		SUM(TransferOrderQty - TransferOrderShippedQty) AS Planned 
	FROM CGWTransferOrder
	WHERE LocationToCode = '02'
		AND LocationFromCode = '01'
	GROUP BY ItemNo
) tr on tr.ItemNo = sku2.Item_No	
WHERE sku2.Location_Code = '02'
	AND sku2.Reordering_Policy != ''
	