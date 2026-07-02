import sqlite3
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
import numpy as np
from pathlib import Path

CONN = sqlite3.connect(Path(__file__).parent / "bc-mirror/bc_mirror.db")

def case_when(period_start):
    period_end = period_start + relativedelta(months=1)
    label = period_start.strftime("%b %Y")
    return (
        f"SUM(CASE WHEN headers.Posting_Date >= '{period_start.strftime('%Y-%m-%d')}' "
        f"AND headers.Posting_Date < '{period_end.strftime('%Y-%m-%d')}' "
        f"THEN lines.Quantity ELSE 0 END) AS \"{label}\""
    )

def run(items=None, customer=None, location=None):
    now = datetime.now()
    
    start = (now.replace(day=1) - relativedelta(months=12))
    periods = 12
    end = start + relativedelta(months=periods)

    lines = []
    lines.append("SELECT lines.No, ")

    dates = []
    for i in range(periods):
        dates.append(case_when(start + relativedelta(months=i)))
    lines.append(", ".join(dates))

    lines.append("FROM Posted_Sales_Invoice_Lines AS lines")
    lines.append("JOIN Posted_Sales_Invoices_Header AS headers")
    lines.append("ON lines.Document_No = headers.No")
    lines.append(f"WHERE headers.Posting_Date >= '{start.strftime('%Y-%m-%d')}'")
    lines.append(f"AND headers.Posting_Date < '{end.strftime('%Y-%m-%d')}'")
    lines.append("AND lines.Type = 'Item'")
    if items:
        items = items.split("|") 
        item_list = ", ".join(f"'{i}'" for i in items)
        lines.append(f"AND lines.No IN ({item_list})")
    if customer:
        lines.append(f"AND lines.Sell_to_Customer_No = '{customer}'")
    if location:
        lines.append(f"AND headers.Location_Code = '{location}'")
    lines.append("GROUP BY lines.No")

    query = " \n".join(lines)

    df = pd.read_sql(query, CONN)

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