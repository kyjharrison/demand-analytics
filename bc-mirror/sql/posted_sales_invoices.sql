CREATE TABLE IF NOT EXISTS posted_sales_invoices (
    invoice TEXT,
    sales_order TEXT, 
    customer TEXT,
    customer_name TEXT,
    currency TEXT, 
    zip TEXT, 
    country TEXT, 
    posting_date TEXT, 
    location TEXT, 
    external_document TEXT, 
    line INTEGER, 
    type TEXT, 
    item TEXT, 
    qty REAL, 
    uom TEXT, 
    price REAL, 
    amt REAL
);
INSERT OR REPLACE INTO posted_sales_invoices
    SELECT 
        h.No AS invoice,
        h.Order_No AS sales_order,
        h.Sell_to_Customer_No AS customer,
        h.Sell_to_Customer_Name AS customer_name,
        h.Currency_Code AS currency,
        h.Ship_to_Post_Code AS zip,
        h.Sell_to_Country_Region_Code AS country,
        h.Posting_Date AS posting_date,
        h.Location_Code AS location,
        h.External_Document_No AS external_document,
        l.Line_No AS line,
        l.Type AS type,
        l.No AS item, 
        l.Quantity AS qty, 
        l.Unit_of_Measure_Code AS uom,
        l.Unit_Price AS price,
        l.Amount AS amt
        PRIMARY KEY (invoice, line)
    FROM raw.Posted_Sales_Invoice_Lines l
    LEFT JOIN raw.Posted_Sales_Invoices_Header h
        ON l.Document_No = h.No
    WHERE h.No >= (SELECT COALESCE(MAX(invoice), '') FROM posted_sales_invoices);