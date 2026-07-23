SELECT
	Entry_No AS entry,
	Posting_Date AS posting_date,
	Entry_Type AS entry_type, 
	Document_Type AS document_type, 
	Document_No AS document, 
	Document_Line_No AS line, 
	Item_No AS item, 
	Item_Description AS description, 
	Description AS description2, 
	Location_Code AS location, 
	Quantity AS qty, 
	Unit_of_Measure_Code AS uom, 
	Source_Type AS source_type, 
	Source_No AS source, 
	Source_Description AS source_description, 
	Source_Order_No AS source_order
FROM Item_Ledger_Entries_Excel
