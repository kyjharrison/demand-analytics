--REPLACE :CUTOFF FOR STANDALONE QUERYING

	WITH daily_ending_balance AS(
		SELECT 
			item,
			registering_date,
			SUM(qty_base) 
				OVER (PARTITION BY item ORDER BY registering_date ASC)
				AS bal,
			ROW_NUMBER() 
				OVER (PARTITION BY item ORDER BY registering_date DESC) 
				AS rn 
			FROM warehouse_entries
		WHERE bin = 'ASSEMBLEOUT' 
			AND item IN (SELECT item FROM bin_contents WHERE bin = 'ASSEMBLEOUT')
	),

	last_emptied AS(
		SELECT item, MAX(registering_date) as last_emptied_date FROM daily_ending_balance
		WHERE ROUND(bal, 5) = 0
		GROUP BY item
	)

	SELECT 
		item,
		MAX(CASE WHEN rn = 1 THEN bal END) as Qty,
		MIN(registering_date) as 'Date Registered' 
		FROM daily_ending_balance
	LEFT JOIN last_emptied USING (item)
	WHERE ROUND(bal, 5) > 0 
		AND registering_date > last_emptied_date
	GROUP BY item
	HAVING MIN(registering_date) < :CUTOFF
	ORDER BY MIN(registering_date)