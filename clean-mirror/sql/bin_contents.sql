SELECT 
    Bin_Code AS Bin, 
    Item_No AS Item, 
    SUM(Qty_Base) AS Qty 
FROM raw.Warehouse_Entries_Excel
WHERE Bin_Code = 'ASSEMBLEOUT'
GROUP BY Bin_Code, Item_No
HAVING Qty_Base > 0
