"""
Pulls from bc_mirror.db and sales_history.py to compile two copies of the SSR report: one for items manufactured at the parent company only, and one for all items. 
Includes inventory on hand 01, 02, 03, and all inventory in transit between warehouses 01, 02, and 03 as "Qty OH". 
This is because parent company wants to know total on hand in the US, not by specific warehouse.
Drops emails in Outlook drafts with reports attached. 
Writes latest data to stable path so that purchaser's Excel workbook can refresh via PowerQuery instead of manual copy-paste.
"""

import sys
import pandas as pd
import json
from pathlib import Path
import sqlite3
from datetime import datetime
import win32com.client
import openpyxl # xlsxwriter output was not triggering OneDrive to sync updates
import sales_history


with open(Path(__file__).parent / "config.json") as f:
    config = json.load(f)

CONN_RAW = sqlite3.connect(Path(config["MIRROR_DIR"]) / "bc_mirror.db")
DIR = config["SSR_DIR"] 

def ssr():

    df = pd.read_sql("""
            SELECT 
                ItemCode as Item, 
                ItemDesc as Description, 
                ItemDesc2 as 'Description 2',
                ProductLine as 'Product Code',
                SubProduct as Subproduct,
                ItemStockUOM as UoM, 
                LifeCycle as Lifecycle, 
                Entity, 
                ItemSupplierCode as Vendor, 
                CostPerUnit as 'Unit Cost'
            FROM CGWItem
            """, CONN_RAW)
    df = df.merge(pd.read_sql("""
            SELECT Item, SUM(Qty) as "Qty OH" 
            FROM (
                SELECT ItemNo as Item, SUM(TransferOrderShippedQty - TransferOrderReceivedQty) AS Qty from CGWTransferOrder
                WHERE LocationFromCode not in ('05', '06')
                GROUP BY Item
                UNION ALL
                SELECT Item_No as Item, SUM(Inventory) as Qty from Stockkeeping_Unit_Card_Excel
                GROUP BY Item
            )
            GROUP BY Item
            """, CONN_RAW), on="Item", how="left")

    df = df.merge(pd.read_sql("""
            SELECT 
                Item_No as Item, 
                SUM(Qty_on_Sales_Order) as 'Qty on SO', 
                SUM(Qty_on_Blanket_Sales_Order) as 'Qty on Blanket SO' 
                from Stockkeeping_Unit_Card_Excel
            GROUP BY Item
            """, CONN_RAW), on="Item", how="left")

    df = df.merge(pd.read_sql("""
            SELECT No as Item, SUM(Outstanding_Quantity) as "Qty on PO" from Purchase_Lines_Excel
            WHERE Type = 'Item'
            GROUP BY Item
            """, CONN_RAW), on="Item", how="left")

    df = df.merge(pd.read_sql("""
            SELECT ItemNo as Item, SUM(TransferOrderQty) as 'Qty in Transit' from CGWTransferOrder
            WHERE LocationFromCode = '06'
            GROUP BY Item
            """, CONN_RAW), on="Item", how="left")

    history = sales_history.run()
    last_12m = history.columns[7:19] # TODO fix to non-positional
    history["Last 12mo"] = history[last_12m].sum(axis=1)
    last_6m = history.columns[13:19] # TODO fix to non-positional
    history["Last 6mo"] = history[last_6m].sum(axis=1)

    df = df.merge(history[["item", "Last 12mo", "Last 6mo"]], left_on="Item", right_on="item", how="left").drop(columns="item")
    df = df[["Item", "Description", "Description 2", "Product Code", "Subproduct", "UoM", "Lifecycle", "Entity", "Vendor", "Unit Cost", "Qty OH", "Qty on PO", "Qty on SO", "Qty on Blanket SO", "Qty in Transit", "Last 12mo", "Last 6mo"]]
    df[["Qty OH", "Qty on PO", "Qty on SO", "Qty on Blanket SO", "Qty in Transit", "Last 12mo", "Last 6mo"]] = df[["Qty OH", "Qty on PO", "Qty on SO", "Qty on Blanket SO", "Qty in Transit", "Last 12mo", "Last 6mo"]].round(0)
    df = df.sort_values('Last 12mo', ascending=False)
    df = df.fillna(0)

    return df


def run():
    df = ssr()

    camel = df[df["Vendor"].isin(["CAMEL", "ATLCA"])]

    # pull list of current containers on the water
    containers = pd.read_sql("""
                    SELECT
                        REPLACE(CGWContainerNo, 'CAMEL ', '') AS Container, 
                        Shipment_Date
                    from Transfer_Order_Excel
                    WHERE CGWContainerNo LIKE '%CAMEL%'
                    """, CONN_RAW).sort_values("Shipment_Date")

    now = datetime.now()

    # save filtered Camel report and email to Camel team
    camel_report = Path(DIR) / f"SSR {now.strftime('%y-%m-%d')} camel.xlsx"
    with pd.ExcelWriter(camel_report, engine='openpyxl') as writer:
        camel.to_excel(writer, index=False, sheet_name='SSR')
        containers.to_excel(writer, index=False, sheet_name='Containers')
        sheet = writer.sheets['SSR']
        format = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
        for row in sheet.iter_rows(min_row=2, min_col=11, max_col=17):
            for cell in row:
                cell.number_format = format
    print(f"Camel SSR written to {camel_report}")

    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = config["camel_team_emails"]
    mail.CC = f'{config["cc_me"]};{config["purchaser_email"]}'
    mail.Attachments.Add(str(camel_report))
    mail.Subject = "SSR"
    mail.HTMLBody = f"""Hello {config['camel_team']},<br><br>
    Here's the latest SSR. Please let me know if there are any issues with the data.<br><br>
    Thank you,<br>
    {config["name"]}<br>
    {config["title"]}
    """
    mail.Display()
    print("Email drafted to Camel team")

    # save full report as dated snapshot
    snapshot = Path(DIR) / f"SSR {now.strftime('%y-%m-%d')}.xlsx"
    with pd.ExcelWriter(snapshot, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='SSR')
        sheet = writer.sheets['SSR']
        format = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
        for row in sheet.iter_rows(min_row=2, min_col=11, max_col=17):
            for cell in row:
                cell.number_format = format
    print(f"Historical snapshot SSR written to {snapshot}")

    # save full report to stable filepath
    stable = Path(DIR) / "SSR.xlsx"
    with pd.ExcelWriter(stable, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='SSR')
        sheet = writer.sheets['SSR']
        format = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
        for row in sheet.iter_rows(min_row=2, min_col=11, max_col=17):
            for cell in row:
                cell.number_format = format
    print("Main SSR file updated")

    # email snapshot to purchaser and alert him his workbook is ready to refresh
    mail = outlook.CreateItem(0)
    mail.To = config["purchaser_email"]
    mail.CC = config["cc_me"]
    mail.Attachments.Add(str(snapshot))
    mail.Subject = "SSR"
    mail.HTMLBody = f"""Hey, {config['purchaser']}, <br><br>
    Here's the latest SSR. Go ahead and refresh your Parameters workbook.<br><br>
    Thank you,<br>
    {config["name"]}<br>
    {config["title"]}
    """
    mail.Display()
    print(f"Email drafted to {config["purchaser"]}")

if __name__ == "__main__":
    run()