DROP TABLE IF EXISTS skus;
CREATE TABLE skus AS
SELECT
    Item_No AS item, 
    Location_Code AS location, 
    Shelf_No AS shelf, 
    Unit_Cost AS unit_cost, 
	COALESCE(oh.qty_oh, 0) AS qty_oh,
	COALESCE(po.qty_on_po, 0) AS qty_on_po,
	COALESCE(so.qty_on_so, 0) AS qty_on_so,
    Replenishment_System AS replenishment_system, 
    Vendor_No AS vendor, 
    Lead_Time_Calculation AS lead_time,
    Vendor_Item_No AS vendor_item, 
    Assembly_Policy AS assembly_policy,
    Reordering_Policy AS reordering_policy,
    Safety_Lead_Time AS safety_lead_time, 
    Minimum_Order_Quantity AS moq, 
    Order_Multiple AS multiple
	
FROM raw.Stockkeeping_Unit_Card_Excel sku

LEFT JOIN (
	SELECT item, location, SUM(qty) as qty_oh
	FROM item_ledger_entries
	GROUP BY item, location
) oh 
	ON oh.item = sku.item 
	AND oh.location = sku.location 

LEFT JOIN (
	SELECT item, location, SUM(qty_outstanding) AS qty_on_po
	FROM purchase_lines
	GROUP BY item, location
) po
	ON po.item = sku.item AND po.location = sku.location 
	
LEFT JOIN (
	SELECT item, location, SUM(qty_outstanding) AS qty_on_so
	FROM sales_lines 
	WHERE blanket_order IS NULL OR blanket_order = ''
	GROUP BY item, location 
) so
	ON so.item = sku.item AND so.location = sku.location 
