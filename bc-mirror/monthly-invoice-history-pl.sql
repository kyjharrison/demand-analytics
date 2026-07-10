SELECT
	strftime('%Y-%m', h.Posting_Date) AS month,
	SUM(l.Quantity) as qty
from Posted_Sales_Invoice_Lines l
LEFT JOIN Posted_Sales_Invoices_Header h
	ON l.Document_No = h.No
WHERE l.No LIKE '%OURTX'
GROUP BY strftime('%Y-%m', h.Posting_Date)
ORDER BY Month DESC