DROP TABLE IF EXISTS sales_lines;
CREATE TABLE sales_lines AS
SELECT 
	sle.Document_Type AS document_type,
	sle.Document_No AS document, 
	sle.Line_No AS line, 
	sle.Sell_to_Customer_No AS customer, 
	sle.Sell_to_Customer_Name AS customer_name,
	sle.Type AS type, 
	sle.No AS item, 
	sle.Description AS description, 
	sle.Unit_of_Measure_Code AS uom,
	sle.Quantity AS qty, 
	sle.Outstanding_Quantity AS qty_outstanding,
	sle.Location_Code AS location, 
	sle.Line_Amount AS amt, 
	so.externalDocumentNumber AS external_document,
	so.orderDate AS order_date, 
	so.shipToCountry AS country, 
	so.shipToState AS state, 
	so.shipToPostCode AS zip, 
	so.currencyCode AS currency, 
	so.status AS status, 
	sol.Blanket_Order_No AS blanket_order
FROM raw.Sales_Lines_Excel sle
LEFT JOIN raw.salesOrders so
	ON sle.Document_No = so.number
LEFT JOIN raw.Sales_Order_Lines sol
	ON sle.Document_No = sol.Document_No
	AND sle.Line_No = sol.Line_No