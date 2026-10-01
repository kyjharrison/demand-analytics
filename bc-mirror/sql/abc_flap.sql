drop table if exists abc_flap;
create table abc_flap as
	with sales as (
		select item, sum(qty) as qty_last_12m from posted_sales_invoice_lines
		where item in (select item from items where product = 'FLAPDISCS')
		and posting_date >= date('now', '-1 year')
		and posting_date < date('now', '-1 day')
		group by item
		order by sum(qty) desc
	)

	select 
		item, 
		qty_last_12m,
		case 
			when qty_last_12m >= 90000
				then '+A'
			when qty_last_12m >= 30000
				then 'A'
			when qty_last_12m >= 12000
				then 'B'
			when qty_last_12m >= 4000
				then 'C'
			else 'D'
		end abc
	from sales