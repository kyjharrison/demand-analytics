SELECT 
    ItemCode AS Item,
    ItemDesc AS Description,
    ItemDesc2 AS Description2,
    ProductLine AS ProductCode,
    SubProduct AS Subproduct,
    ItemSupplierCode AS Vendor,
    LifeCycle AS LC,
    ItemStockUOM AS UoM,
    CostPerUnit AS UnitCost
FROM raw.CGWItem