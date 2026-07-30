DROP TABLE IF EXISTS bin_contents;
CREATE TABLE bin_contents AS
SELECT 
    Bin_Code AS bin, 
    Item_No AS item, 
    SUM(Qty_Base) AS qty 
FROM raw.Warehouse_Entries_Excel
GROUP BY Bin_Code, Item_No
HAVING SUM(Qty_Base) > 0;
