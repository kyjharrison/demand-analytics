SELECT 
    h.No AS Invoice,
    h.Order_No AS Sales_Order,
    h.Sell_to_Customer_No AS Customer,
    h.Sell_to_Customer_Name AS Customer_Name,
    h.Currency_Code AS Currency,
    h.Ship_to_Post_Code AS ZIP,
    h.Sell_to_Country_Region_Code AS Country,
    h.Posting_Date AS Posting_Date,
    h.Location_Code AS Location,
    h.External_Document_No,
    l.Line_No AS Line,
    l.Type,
    l.No AS Item, 
    l.Quantity, 
    l.Unit_of_Measure_Code AS UoM,
    l.Unit_Price AS Price,
    l.Amount
FROM raw.Posted_Sales_Invoice_Lines l
LEFT JOIN raw.Posted_Sales_Invoices_Header h
    ON l.Document_No = h.No