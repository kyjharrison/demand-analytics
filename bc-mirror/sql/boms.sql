DROP TABLE IF EXISTS boms;
CREATE TABLE boms AS
SELECT 
    Parent_Item_No AS item, 
    Line_No AS line, 
    No AS component, 
    Quantity_per AS qty, 
    Unit_of_Measure_Code AS uom
FROM raw.Assembly_BOM_Excel;