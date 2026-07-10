CLEAN_TABLES = {
    "item": 
        """
        SELECT 
            ItemCode AS Item,
            ItemDesc AS Description,
            ItemDesc2 AS Description2,
            ProductLine AS ProductCode,
            SubProduct AS Subproduct,
            ItemSupplierCode AS Vendor,
            LifeCycle AS LC,
            ItemStockUOM AS UoM,
            CostPerUnit AS UnitCost
        FROM CGWItem
        """,
    "sku": 
        """
        SELECT
            Item_No AS Item, 
            Location_Code AS Location, 
            Shelf_No AS Shelf_No, 
            Unit_Cost, 
            Replenishment_System, 
            Vendor_No AS Vendor, 
            Lead_Time_Calculation AS Lead_Time,
            Vendor_Item_No, 
            Assembly_Policy,
            Reordering_Policy,
            Safety_Lead_Time, 
            Minimum_Order_Quantity AS MOQ, 
            Order_Multiple AS Multiple
        FROM Stockkeeping_Unit_Card_Excel
        """,
    "posted_sales_invoices":
        """
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
        FROM Posted_Sales_Invoice_Lines l
        LEFT JOIN Posted_Sales_Invoices_Header h
            ON l.Document_No = h.No
        """,
    "bin_contents":
        """
        Select 
            Bin_Code,
            Item_No AS Item, 
            SUM(Quantity) AS Qty,
            Unit_of_Measure_Code AS UoM
        FROM Warehouse_Entries_Excel
        GROUP BY Bin_Code, Item_No, Unit_of_Measure_Code
        HAVING SUM(Quantity) > 0
        """
}
