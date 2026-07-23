SELECT 
    Bin_Code AS bin, 
    Item_No AS item, 
    SUM(Qty_Base) AS qty 
FROM raw.Warehouse_Entries_Excel
WHERE Bin_Code = 'ASSEMBLEOUT'
GROUP BY Bin_Code, Item_No
HAVING Qty_Base > 0
