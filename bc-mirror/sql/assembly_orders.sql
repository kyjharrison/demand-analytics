DROP TABLE IF EXISTS assembly_orders;
CREATE TABLE assembly_orders AS
SELECT
	No AS assembly, 
	Item_No AS item, 
	Description AS description, 
	Quantity AS qty, 
	Posting_Date AS posting_date, 
	Due_Date as due_date, 
	Starting_Date AS starting_date, 
	Ending_Date AS ending_date, 
	Remaining_Quantity AS qty_remaining, 
	Assembled_Quantity AS qty_assembled, 
	Status AS status, 
	Location_Code AS location, 
	Unit_Cost AS cost, 
	Cost_Amount AS amt, 
	Shortcut_Dimension_1_Code AS product 
FROM raw.Assembly_Order_Excel