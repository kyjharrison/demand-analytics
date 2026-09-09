CREATE TABLE IF NOT EXISTS posted_assembly_orders (
    posted_assembly TEXT PRIMARY KEY,
    assembly TEXT, 
    item TEXT,
    qty TEXT, 
	uom TEXT,
    posting_date TEXT, 
	starting_date TEXT,
    location TEXT, 
	bin TEXT,
	cost REAL, 
	amt REAL,
	user TEXT
);
INSERT OR REPLACE INTO posted_assembly_orders
    SELECT 
        No AS posted_assembly, 
        Order_No AS assembly, 
		Item_No AS item, 
		Quantity AS qty, 
		Unit_of_Measure_Code AS uom, 
		Posting_Date AS posting_date, 
		Starting_Date AS starting_date, 
		Location_Code AS location,
		Bin_Code AS bin, 
		Unit_Cost AS cost,
		Cost_Amount AS amt,
		User_ID AS user
    FROM raw.Posted_Assembly_Order_Excel
    WHERE No >= (SELECT COALESCE(MAX(posted_assembly), '') FROM posted_assembly_orders);