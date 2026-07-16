SELECT
	Entry_No,
	Posting_Date,
	Entry_Type, 
	Document_Type, 
	Document_No as Document, 
	Document_Line_No as Line, 
	Item_No as Item, 
	Item_Description as Description, 
	Description as Description_2, 
	Location_Code as Location, 
	Quantity as Qty, 
	Unit_of_Measure_Code as UoM, 
	Source_Type, 
	Source_No, 
	Source_Description, 
	Source_Order_No
FROM Item_Ledger_Entries_Excel
