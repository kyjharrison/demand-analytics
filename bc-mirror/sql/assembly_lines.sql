DROP TABLE IF EXISTS assembly_lines;
CREATE TABLE assembly_lines AS
SELECT
	al.Document_No AS assembly_order,
	al.Line_No AS line,
	al.No AS component, 
	al.Description AS component_description,
	al.Description_2 as component_description2,
	al.Shortcut_Dimension_1_Code AS component_product,
	al.Unit_of_Measure_Code AS component_uom,
	al.Quantity_per AS qty_per, 
	al.Quantity AS component_qty,
	al.Consumed_Quantity AS component_qty_consumed, 
	al.Remaining_Quantity AS component_qty_remaining, 
	ao.Item_No AS item, 
	ao.Description AS description, 
	ao.Description_2 AS description2,
	ao.Quantity AS qty, 
	ao.Quantity_to_Assemble AS qty_to_assemble,
	ao.Posting_Date AS posting_date, 
	ao.Due_Date AS due_date, 
	ao.Starting_Date AS starting_date, 
	ao.Ending_Date AS ending_date, 
	ao.Remaining_Quantity AS qty_remaining, 
	ao.Assembled_Quantity AS qty_assembled, 
	ao.Status AS status, 
	ao.Unit_Cost AS cost, 
	ao.Cost_Amount AS amt, 
	ao.Shortcut_Dimension_1_Code AS product
FROM raw.Assembly_Lines_Excel al
LEFT JOIN raw.Assembly_Order_Excel ao
ON al.Document_No = ao.No
