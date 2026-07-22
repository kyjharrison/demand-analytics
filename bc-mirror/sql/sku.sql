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
FROM raw.Stockkeeping_Unit_Card_Excel