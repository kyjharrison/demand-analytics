SELECT 
    ItemCode AS item,
    ItemDesc AS description,
    ItemDesc2 AS description2,
    ProductLine AS product,
    SubProduct AS subproduct,
    ItemSupplierCode AS vendor,
    LifeCycle AS lc,
    ItemStockUOM AS uom,
    CostPerUnit AS unit_cost
FROM raw.CGWItem