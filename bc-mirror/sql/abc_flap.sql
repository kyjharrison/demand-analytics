drop table if exists abc_flap;
create table abc_flap as
	with sales as (
		select 
			i.item, 
			i.lc, 
			coalesce(sum(psi.qty), 0) as qty_last_12m 
		from items i
		left join posted_sales_invoice_lines psi
			on psi.item = i.item 
			and psi.posting_date >= date('now', '-1 year')
			and psi.posting_date < date('now', '-1 day')
		where i.product = 'FLAPDISCS'
		group by i.item
		order by sum(psi.qty) desc
	)

	select 
		item, 
		lc,
		qty_last_12m,
		case 
			when lc not in ('STK', 'CSS')
				then lc
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