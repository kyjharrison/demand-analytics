CREATE TABLE IF NOT EXISTS item_ledger_entries (
    entry INTEGER PRIMARY KEY,
    posting_date TEXT,
    entry_type TEXT,
    document_type TEXT,
    document TEXT,
    line INTEGER,
    item TEXT,
    description TEXT,
    description2 TEXT,
    location TEXT,
    qty REAL,
    uom TEXT,
    source_type TEXT,
    source TEXT,
    source_description TEXT,
    source_order TEXT
);
INSERT OR REPLACE INTO item_ledger_entries
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
	FROM raw.Item_Ledger_Entries_Excel
	WHERE Entry_No >= (SELECT COALESCE(MAX(entry), 0) FROM item_ledger_entries);
