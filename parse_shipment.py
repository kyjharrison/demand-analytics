"""
Takes container number as argument. 
Fetches corresponding container docs from In Transit folder.
Fetches latest PURLINES config package download from Downloads folder. 
Outputs pastable table into terminal.
"""

import pandas as pd
import sys
import pathlib
from datetime import datetime
import re
import pyperclip

IN_TRANSIT_FOLDER_PATH = pathlib.Path(r"C:\Users\Ky.Harrison\OneDrive - CGW Abrasives\Shared Documents\In Transit")
DOWNLOADS_PATH = pathlib.Path(r"C:\Users\Ky.Harrison\Downloads")
PO_CROSSWALK = pathlib.Path(r"C:\Users\Ky.Harrison\OneDrive - CGW Abrasives\PO0009468  PO0009470.xlsx")

ALIASES = {
    "External Document No": "External Document No.",
    "Qty Shipped": "Qty Shipped ",
}

def find_invoice(container):
    while True:
        for folder in IN_TRANSIT_FOLDER_PATH.iterdir():
            if container in folder.name:
                files = list(folder.glob("*.xlsx"))
                number = len(files)
                if number == 0:
                    print("No .xlsx found")
                    sys.exit(1)
                if number > 1:
                    for i, file in enumerate(files):
                        print(f"[{i}] {file}")
                    choice = int(input("Which file? "))
                    return files[choice]            
                return files[0] # path object
        print("Container not found in the In Transit folder.")
        input("Try again?")

def update_po_numbers(invoice_df):
    crosswalk = pd.read_excel(PO_CROSSWALK).set_index("Original PO #")["PO"].to_dict()
    old_po = invoice_df["po"].copy()
    invoice_df["po"] = invoice_df["po"].map(crosswalk).fillna(invoice_df["po"])
    changed_filter = old_po != invoice_df["po"]
    changes = zip(old_po[changed_filter], invoice_df["po"][changed_filter])
    if changed_filter.any():
        for old, new in changes:
            print(f"Updated {old} -> {new}")
    else:
        print("No old PO numbers found. Proceeding...")
    return invoice_df

def parse_camel_invoice(filepath):
    """Searches In Transit folder for container number, finds matching folder, pulls xlsx invoice in as a dataframe, and returns the filter_string, the po_list, and the aggregated qties by po_item"""
    df = pd.read_excel(filepath)
    df = df.rename(columns=ALIASES)

    shipment_date_raw = df["Date Shipped "].iloc[0]
    shipment_date_norm = shipment_date_raw.replace('/', '.').replace('-', '.')
    shipment_date = datetime.strptime(shipment_date_norm, "%m.%d.%Y").strftime("%Y-%m-%d")

    for col in ["External Document No.", "Customer P/N", "Qty Shipped "]:
        if df[col].isna().any():
            print(f"Warning: missing values in '{col}' column. Check file and rerun.")
            sys.exit(1)
    df["po_stripped"] = df["External Document No."].apply(lambda x: re.sub(r"\D", "", x))
    df["po"] = df["po_stripped"].apply(lambda x: f"PO{x.zfill(7)}")

    # check against ATLCA PO migration and update PO numbers
    df = update_po_numbers(df)

    df["po_item_key"] = df.apply(lambda row: f"{row['po']}|{row['Customer P/N'].replace('-','')}", axis=1)
    aggregated_df = df.groupby("po_item_key")["Qty Shipped "].sum().reset_index()
    invoice_dict = aggregated_df.set_index("po_item_key")["Qty Shipped "].to_dict()
    po_list = df["po"].unique().tolist()
    filter_string = "|".join(po_list)
    return invoice_dict, po_list, filter_string, shipment_date # tuple

def find_purlines():
    required_columns = ["Document No.", "Line No.", "No.", "Quantity", "Qty. to Receive", "Quantity Received"]
    while True:
        files = list(DOWNLOADS_PATH.glob("Default*.xlsx"))
        newest = max(files, key=lambda x: x.stat().st_mtime)
        today = datetime.today().date()
        if datetime.fromtimestamp(newest.stat().st_mtime).date() != today:
            print("Warning: no recent config pkg download found")
            input("Try again?")
            continue
        df = pd.read_excel(newest, header=2)
        columns = df.columns.tolist()
        try:
            start = columns.index("Document No.")
            if columns[start:start + len(required_columns)] != required_columns:
                raise ValueError
            break
        except ValueError:
            print(f"Warning: PURLINES download needed with {required_columns}")
            input("Try again?")
    return df

def clean_purlines(df, po_list):
    df = df[df["Document No."].isin(po_list)]
    df["po_item_key"] = df.apply(lambda row: f"{row['Document No.']}|{row['No.'].replace('-','')}", axis=1)
    df["qty_remaining"] = df["Quantity"] - df["Quantity Received"]
    df.loc[:, "Qty. to Receive"] = 0
    return df

def update_qty_to_receive(aggregated_invoice, cleaned_purlines): # dict, df
    lines = []
    for key, group in cleaned_purlines.groupby("po_item_key"):
        if key in aggregated_invoice:
            remaining = aggregated_invoice[key]
            open_lines = group[group["qty_remaining"]>0].sort_values("Line No.")
            if open_lines.empty:
                group.loc[group["Line No."].idxmax(), "Qty. to Receive"] = remaining
            else:
                for idx, line in open_lines.iterrows():
                    if remaining > line["qty_remaining"]:
                        group.loc[idx, "Qty. to Receive"] = line["qty_remaining"]
                        remaining = remaining - line["qty_remaining"]
                    else:
                        group.loc[idx, "Qty. to Receive"] = remaining
                        remaining = 0
                        break
                if remaining > 0:
                    group.loc[open_lines.index[-1], "Qty. to Receive"] += remaining
            lines.append(group)
    return pd.concat(lines) # returns df

def summarize_for_transfer(aggregated_invoice_dict):
    invoice = pd.Series(aggregated_invoice_dict).reset_index()
    invoice.columns = ["po_item", "qty"]
    invoice[["po", "item"]] = invoice["po_item"].str.split("|", expand=True)
    transfer = (invoice
            .groupby("item")["qty"]
            .sum()
            .sort_index()
        )
    return transfer.to_dict()

def main():
    if len(sys.argv) < 2:
        print("Must specify a container number to process")
        sys.exit(1)
    else:
        container = sys.argv[1]
    aggregated_invoice, po_list, filter_string, shipment_date = parse_camel_invoice(find_invoice(container))
    cleaned_purlines = clean_purlines(find_purlines(), po_list)
    lines = update_qty_to_receive(aggregated_invoice, cleaned_purlines)
    invoice = set(aggregated_invoice)
    purlines = set(cleaned_purlines["po_item_key"])
    missing = invoice - purlines
    if missing:
        for po_item in missing:
            print(f"{po_item} — {aggregated_invoice[po_item]}")
        input("These lines not found in purlines file. Press Enter to continue...")

    with pd.ExcelWriter("output.xlsx") as writer:
        lines.to_excel(writer, sheet_name="Lines")

    input("Results written to output.xlsx. Press Enter to copy filter string to clipboard...")

    pyperclip.copy(filter_string)
    print(filter_string)
    input("Filter string copied. Press Enter to copy container number to clipboard...")

    transfer_container = f"CAMEL {container}"
    pyperclip.copy(transfer_container)
    print(transfer_container)
    input("Container number copied. Press Enter to copy items to clipboard...")

    transfer = summarize_for_transfer(aggregated_invoice)

    pyperclip.copy("\n".join(transfer))
    input("Items list copied. Press Enter to continue...")

    for item, qty in transfer.items():
        print(item, qty)

if __name__ == "__main__":
    main()


