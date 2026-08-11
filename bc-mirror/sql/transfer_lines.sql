DROP TABLE IF EXISTS transfer_lines;
CREATE TABLE transfer_lines AS
SELECT
    TransferOrderNumber AS transfer,
    TransferOrderLineNumber AS line,
    ItemNo AS item,
    TransferOrderQty AS qty,
    TransferOrderShippedQty AS qty_shipped,
    TransferOrderReceivedQty AS qty_received,
    TransferOrderStatus AS status,
	LocationFromCode AS location_from,
    LocationToCode AS location_to,
    TransferOrderDate AS posting_date,
    TransferOrderExpectedReceiptDate AS expected_receipt_date
FROM raw.CGWTransferOrder;