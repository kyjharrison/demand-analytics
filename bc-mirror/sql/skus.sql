SELECT
    Item_No AS item, 
    Location_Code AS location, 
    Shelf_No AS shelf, 
    Unit_Cost AS unit_cost, 
    Replenishment_System AS replenishment_system, 
    Vendor_No AS vendor, 
    Lead_Time_Calculation AS lead_time,
    Vendor_Item_No AS vendor_item, 
    Assembly_Policy AS assembly_policy,
    Reordering_Policy AS reordering_policy,
    Safety_Lead_Time AS safety_lead_time, 
    Minimum_Order_Quantity AS moq, 
    Order_Multiple AS multiple
FROM raw.Stockkeeping_Unit_Card_Excel