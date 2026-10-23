import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", sql_output="pandas")


@app.cell
def _():
    import marimo as mo
    import math
    import sqlite3 as sql

    db = r"C:\Demand Analytics\public\bc-mirror\clean_mirror.db"
    conn = sql.connect(db)
    return conn, math, mo


@app.cell
def _(conn, mo):
    sales = mo.sql(
        f"""
        select 
            strftime('%Y-%m', posting_date) as month,
            item, 
            sum(qty) as qty_sold
        from posted_sales_invoice_lines
        where location = '01'
        group by strftime('%Y-%m', posting_date), item
        """,
        engine=conn
    )
    return


@app.cell
def _(conn, mo):
    items_raw = mo.sql(
        f"""
        select 
        	s.item, 
            s.location, 
            s.lead_time,
            i.lc
        from skus s
        left join items i using(item)
        where s.location = '01'
        	and i.lc in ('CSS', 'STK')
        	and item != '99997'
        """,
        engine=conn
    )
    return (items_raw,)


@app.cell
def _(items_raw, math):
    items = (
        items_raw
        .assign(
            lead_time_months=items_raw["lead_time"].apply(
                lambda x: 1 if "D" in str(x) else math.ceil(int(str(x)[:-1]) / 4)
            )
        )
    )
    items
    return


if __name__ == "__main__":
    app.run()
