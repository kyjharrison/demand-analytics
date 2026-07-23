import sqlite3
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
import numpy as np
from pathlib import Path
import json

with open(Path(__file__).parent.parent / "internal/config.json") as f:
    config = json.load(f)
CONN_CLEAN = sqlite3.connect(Path(config["MIRROR_DIR"]) / "clean_mirror.db")

def case_when(period_start):
    period_end = period_start + relativedelta(months=1)
    label = period_start.strftime("%b %Y")
    return (
        f"SUM(CASE WHEN posting_date >= '{period_start.strftime('%Y-%m-%d')}' "
        f"AND posting_date < '{period_end.strftime('%Y-%m-%d')}' "
        f"THEN qty ELSE 0 END) AS \"{label}\""
    )

def run(items=None, customer=None, location=None):
    now = datetime.now()
    
    start = (now.replace(day=1) - relativedelta(months=12))
    periods = 12
    end = start + relativedelta(months=periods)

    lines = []
    lines.append("SELECT item, i.description, i.description2, i.product, i.subproduct, i.vendor, i.lc, ")

    dates = []
    for i in range(periods):
        dates.append(case_when(start + relativedelta(months=i)))
    lines.append(", ".join(dates))

    lines.append("FROM posted_sales_invoices psi")
    lines.append("JOIN items i")
    lines.append("USING (item)")
    lines.append(f"WHERE psi.posting_date >= '{start.strftime('%Y-%m-%d')}'")
    lines.append(f"AND psi.posting_date < '{end.strftime('%Y-%m-%d')}'")
    lines.append("AND psi.type = 'Item'")
    if items:
        items = items.split("|") 
        item_list = ", ".join(f"'{i}'" for i in items)
        lines.append(f"AND item IN ({item_list})")
    if customer:
        lines.append(f"AND psi.customer = '{customer}'")
    if location:
        lines.append(f"AND psi.location = '{location}'")
    lines.append("GROUP BY item, i.description, i.description2, i.product, i.subproduct, i.vendor, i.lc")

    query = " \n".join(lines)

    df = pd.read_sql(query, CONN_CLEAN)

    last_12m = df.columns[1:]
    df["12m_avg"] = df[last_12m].mean(axis=1).round(0).astype(int)
    last_3m = last_12m[-3:]
    df["3m_avg"] = df[last_3m].mean(axis=1).round(0).astype(int)
    df["12m_peak"] = df[last_12m].max(axis=1)
    df["3m_peak"] = df[last_3m].max(axis=1)
    df["trend"] = (df["3m_avg"] / df["12m_avg"]).round(1)
    df["cv"] = (df[last_12m].std(axis=1) / df["12m_avg"]).round(1)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.sort_values('12m_avg', ascending=False)

    return df
    
if __name__ == "__main__":

    now = datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument("--items")
    parser.add_argument("--customer")
    parser.add_argument("--location")

    """
    parser.add_argument("--start") 
    parser.add_argument("--grain") 
    parser.add_argument("--periods") # TODO later add month-to-date
    parser.add_argument("--uom")
    parser.add_argument("--state")
    """
    args = parser.parse_args()

    df = run(items=args.items, customer=args.customer, location=args.location)

    filename = f"sales-history-{now.strftime('%y-%m-%d')}.xlsx"
    with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales History')
        workbook = writer.book
        worksheet = writer.sheets['Sales History']
        num_format = workbook.add_format({'num_format': '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'})
        pct_format = workbook.add_format({'num_format': '0%'})
        worksheet.add_table(0, 0, len(df), len(df.columns)-1, {
            'style': 'None',
            'columns': [
                {'header': df.columns[0]}
            ] + [
                {'header': col} for col in df.columns[1:]
            ]
        })
        worksheet.set_column(1, len(df.columns)-3, None, num_format)
        worksheet.set_column(len(df.columns)-1, len(df.columns)-1, None, pct_format)

    print(f"Completed in {datetime.now() - now}")

    os.startfile(filename)