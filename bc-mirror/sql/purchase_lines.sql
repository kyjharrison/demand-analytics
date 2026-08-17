DROP TABLE IF EXISTS purchase_lines;
CREATE TABLE purchase_lines AS
SELECT
    pl.Document_Type AS doc_type,
    pl.Document_No AS purchase_order,
    pl.Line_No AS line,
    pl.Buy_from_Vendor_No AS vendor,
	pl.Type as type,
    pl.No AS item,
    pl.Description AS description,
    pl.Location_Code AS location,
    pl.Quantity AS qty,
    pl.Outstanding_Quantity AS qty_outstanding,
    pl.Unit_of_Measure_Code AS uom,
    pl.Direct_Unit_Cost AS unit_cost,
    po.currencyCode AS currency_code,
    po.orderDate AS order_date,
	pl.Promised_Receipt_Date AS promised_receipt_date,
    pl.Expected_Receipt_Date AS expected_receipt_date,
    po.status AS status
FROM raw.Purchase_Lines_Excel pl
LEFT JOIN raw.purchaseOrders po
    ON pl.Document_No = po.number
WHERE pl.Document_Type = 'Order';