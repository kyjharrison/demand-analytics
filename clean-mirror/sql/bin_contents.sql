SELECT 
    Bin_Code, 
    Item_No, 
    SUM(Qty_Base) AS Qty 
FROM raw.Warehouse_Entries_Excel
WHERE Bin_Code = 'ASSEMBLEOUT'
GROUP BY Bin_Code, Item_No
HAVING Qty >0
