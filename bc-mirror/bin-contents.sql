select Bin_Code, Item_No, SUM(Quantity) as Qty from Warehouse_Entries_Excel
WHERE Bin_Code = 'ASSEMBLEOUT'
GROUP BY Bin_Code, Item_No
HAVING Qty >0
