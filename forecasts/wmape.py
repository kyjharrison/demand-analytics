import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", sql_output="pandas")


@app.cell
def _():
    import io
    import marimo as mo
    import math
    import pandas as pd
    import sqlite3 as sql

    db = r"C:\Demand Analytics\public\bc-mirror\clean_mirror.db"
    conn = sql.connect(db)
    return conn, io, mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### date-shifted sales history
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    month_input = mo.ui.text(value="2025-04", label="Ending month (YYYY-MM)")
    month_input
    return (month_input,)


@app.cell(hide_code=True)
def _(conn, month_input, pd):
    # convert input output to date string
    end = month_input.value + "-01"

    # pull full list of stk/css items
    items = pd.read_sql(
        "SELECT item FROM items WHERE lc IN ('STK', 'CSS')",
        conn
    )

    # pull sales history
    query = """
        select 
        	item, 
        	date(posting_date, 'start of month') as month, 
        	sum(qty) as qty_sold
        from posted_sales_invoice_lines
        where posting_date >= date(:end, '-36 months')
            and posting_date < :end 
            and location = '01'
            and item in (select item from items where lc in('STK', 'CSS'))
        group by item, date(posting_date, 'start of month')
    """
    sales = pd.read_sql(query, conn, params={"end": end})


    # # demand classification logic
    # def classify(item)
    #     cv_cutoff = 0.49
    #     adi_cutoff = 1.32    
    #     all_months = pd.date_range(
    #         end=pd.Timestamp(end) - pd.DateOffset
    #     )
    #     item_history = item.set_index("month")["qty_sold"].reindex(all_months, fill_value=0)
    #     n_nonzero = (item_history > 0).sum()

    #     if n_nonzero == 0:
    #         return pd.Series({"cv": None, "adi": None, "classification": "no demand"})

    #     adi = 



    # pivot to wide format for upload
    wide = (
        sales
        .pivot_table(index=["item"], 
                  columns="month",
                  values="qty_sold",
                  fill_value=0)
        .reindex(items["item"], fill_value=0)
        .reset_index()
    )
    wide.insert(1, "location", "01")
    wide
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## forecast analysis
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    files = mo.ui.file(multiple=True, kind="area")
    files
    return (files,)


@app.cell
def _(files, io, pd):
    def transform_forecast(file):
        date_str = file.name.replace("fc ", "").replace(".csv", "")
        forecast_date = pd.Timestamp(date_str)
        periods = pd.date_range(start=forecast_date, periods=12, freq='MS')
        fc = pd.read_csv(io.BytesIO(file.contents), header=4, dtype={'Location': str})
        fc = (
            fc
            .iloc[:, 1:]
            .dropna(how='all')
            .set_axis(['SKU', 'Location'] + list(periods.strftime('%Y-%m-%d')), axis=1)
            .melt(id_vars=['SKU', 'Location'], var_name='forecast_period', value_name='qty')
            .assign(forecast_date=forecast_date)
            [['forecast_date', 'SKU', 'Location', 'forecast_period', 'qty']]
        )
        return fc

    forecasts = [transform_forecast(f) for f in files.value if f.name.endswith(".csv")]
    df = pd.concat(forecasts, ignore_index=True)

    df
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
