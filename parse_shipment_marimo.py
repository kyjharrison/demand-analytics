import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    #TODO get new Entra app registration with permissions scoped to PATCH and POST against tables 38, 39, 5740, 5741 (purchase headers, purchase lines, transfer headers, transfer lines). not to post receipts just to do the data entry. 
    return


@app.cell
def _():
    #TODO snap to first day of current month if shipment date is previous month
    return


@app.cell
def _():
    #TODO add list of discrepancies between total receipts and sales orders
    return


@app.cell
def _():
    #TODO add auto-open filtered list of orders to closeoutlist of orders to closeout and auto-open filtered list 
    return


@app.cell
def _():
    #TODO add logger
    return


@app.cell
def _():
    #TODO any lines missing from PURLINES (like the -V vallen items don't get added to the transfer, need to fix that)
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import io
    import json
    import os
    import requests
    import sys
    import time
    import webbrowser

    from datetime import datetime
    from pathlib import Path

    import pandas as pd
    import pdfplumber
    import pyperclip
    import re

    sys.path.insert(0, str(Path(__file__).parent / "bc-mirror"))
    from bc_keyvault_auth import build_bc_odata_base_url, get_bc_connection

    BC_CONFIG, BC_HEADERS = get_bc_connection()
    base = build_bc_odata_base_url(BC_CONFIG)

    with open(Path(__file__).parent / "config.json") as config:
        config = json.load(config)

    TRANSIT_DIR = Path(config["TRANSIT_DIR"])
    DOWNLOADS_DIR = Path(config["DOWNLOADS_DIR"])
    BC_BASE = config["BC_BASE"]

    CAMEL_BUFFER_DAYS = 84
    ATLCA_BUFFER_DAYS = 7
    TRANSIT_DAYS = 42
    return (
        ATLCA_BUFFER_DAYS,
        BC_BASE,
        BC_CONFIG,
        BC_HEADERS,
        CAMEL_BUFFER_DAYS,
        DOWNLOADS_DIR,
        TRANSIT_DAYS,
        TRANSIT_DIR,
        build_bc_odata_base_url,
        datetime,
        io,
        mo,
        os,
        pd,
        pdfplumber,
        pyperclip,
        re,
        requests,
        time,
        webbrowser,
    )


@app.cell(hide_code=True)
def _(mo):
    files = mo.ui.file(multiple=True, kind="area")
    files
    return (files,)


@app.cell(hide_code=True)
def _(files, mo):
    file_list_display = ""
    if files.value:
        file_list_display += "Uploaded files: \n\n"
        file_list_display += "  \n".join(f.name for f in files.value)
    mo.md(file_list_display)
    return


@app.cell(hide_code=True)
def _(files, io, mo, pd, pdfplumber, re):
    HEADER = ["No", "PONo", "YourPN", "ItemPN", "ItemDescription", "Qty", "UnitPrice", "TotalAmount"]
    DF_COLUMNS = ["invoice"] + HEADER

    containers = set()
    invoice_dates = set()
    lines = []
    file_count = 0

    for uploaded in files.value:
        if uploaded.name.startswith("Invoice") and uploaded.name.endswith(".pdf"): # drag-and-drop all docs but only parse invoices
            invoice_num = uploaded.name.split()[1] 
            file_count += 1

            invoice_container = None
            invoice_date = None
            collecting_lines = False # state flag marking whether header row has been found for this file

            with pdfplumber.open(io.BytesIO(uploaded.contents)) as pdf:
                for page in pdf.pages:
                    for table in page.extract_tables():

                        # look for container and date until found
                        if not invoice_container:
                                for row in table:
                                    for cell in row:
                                        if cell:
                                            match = re.search(r'Date:\s*(\d{2}/\w{3}/\d{2})', cell)
                                            if match:
                                                invoice_dates.add(pd.to_datetime(match.group(1), format='%d/%b/%y'))
                                            match = re.search(r'Container:\s*([A-Z]{4}\s?\d{7})', cell)
                                            if match:
                                                containers.add(match.group(1).replace(' ', ''))

                        # collect invoice lines 
                        for row in table:
                            if [cell.replace(" ", "") if cell else cell for cell in row] == HEADER: #strips spaces before comparing to header
                                collecting_lines = True # flip the state flag
                                continue
                            if collecting_lines and len(row) == 8 and (row[1] or row[2]): # skip lines with neither PO nor item (such as the freight charge line)
                                lines.append([invoice_num] + row)

    invoice_raw = pd.DataFrame(lines, columns=DF_COLUMNS)


    # confirm document parsing and get user input if needed
    invoice_confirmation_display = f"{file_count} invoices found \n\n"

    date_picker = None
    if len(invoice_dates) > 1:
        date_picker = mo.ui.dropdown(options={d.strftime("%Y-%m-%d"): d for d in invoice_dates}, label="Select")

        invoice_confirmation_display += f"**WARNING — MULTIPLE DATES:** {invoice_dates} \n\nPlease check that all documents uploaded belong to the same shipment. \n\n"
        invoice_confirmation_display += f"To process all {file_count} invoices as a single container, please choose which date to use: \n\n{date_picker} \n\n"

    container_picker = None
    if len(containers) > 1:
        container_picker = mo.ui.dropdown(options={c: c for c in containers}, label="Select")
        invoice_confirmation_display += f"**WARNING — MULTIPLE CONTAINER NUMBERS:** {containers} \n\nPlease check that all documents uploaded belong to the same shipment. \n\n"
        invoice_confirmation_display += f"To process all {file_count} invoices as a single container, please choose which container number to use: \n\n{container_picker} \n\n"

    mo.md(invoice_confirmation_display)
    return (
        container_picker,
        containers,
        date_picker,
        invoice_dates,
        invoice_raw,
    )


@app.cell(hide_code=True)
def _(container_picker, containers, date_picker, invoice_dates, mo):
    if date_picker is not None:
        shipment_date = date_picker.value
    else:
        shipment_date = next(iter(invoice_dates))
    date_str = shipment_date.strftime("%Y-%m-%d")

    if container_picker is not None:
        container = container_picker.value
    else:
        container = next(iter(containers))

    shipment_date, container

    mo.md(f"**Shipment date:** {date_str} \n\n**Container:** {container}")
    return container, shipment_date


@app.cell(hide_code=True)
def _(invoice_raw, mo):
    # prompt user to enter a PO number for lines with no PO listed

    po_inputs = {}
    missing_po = invoice_raw[invoice_raw["PONo"] == ""]
    po_input_display = None

    if not missing_po.empty:
        missing_po_table = "| invoice | item | qty |  |\n|---|---|---|---|\n"
        for idx, r in missing_po.iterrows():
            inp = mo.ui.text(placeholder="Enter PO")
            po_inputs[idx] = inp
            missing_po_table += f"| {r['invoice']} | {r['YourPN']} | {r['Qty']} | {inp} |\n"
        po_input_display = mo.md(f"**{len(missing_po)} item(s) with no PO.** \n\n Please enter a PO number to receive against:\n\n{missing_po_table}")

    po_input_display
    return (po_inputs,)


@app.cell
def _(invoice_raw, po_inputs):
    # incorporate the user's inputs into the final dataframe
    patched = invoice_raw.copy()
    if po_inputs:
        for index, input_po, in po_inputs.items():
            if input_po.value:
                patched.loc[index, "PONo"] = input_po.value

    camel_invoice = (
        patched
        .assign(
            Qty=lambda d: d["Qty"].str.replace(",","").astype(float).astype(int),
            po_stripped=lambda d: d["PONo"].str.replace(r"\D", "", regex=True),
            po=lambda d: "PO"+ d["po_stripped"].str.zfill(7),
            item=lambda d: d["YourPN"].str.replace("-", "", regex=False),
            po_item_key=lambda d: d["po"] + "|" + d["item"]
        )
        .rename(columns={"No": "line", "ItemDescription": "description", "Qty": "qty_shipped"})
        [["invoice", "line", "po", "item", "description", "qty_shipped", "po_item_key",]]
    )

    invoice_dict = (
        camel_invoice
            .groupby("po_item_key")["qty_shipped"].sum().reset_index()
            .set_index("po_item_key")["qty_shipped"].to_dict()
    )

    po_list = camel_invoice["po"].unique().tolist()
    filter_string = "|".join(po_list)

    camel_invoice

    return camel_invoice, filter_string, invoice_dict, po_list


@app.cell
def _(BC_CONFIG, BC_HEADERS, build_bc_odata_base_url, pd, po_list, requests):
    odata_base = build_bc_odata_base_url(BC_CONFIG)
    odata_filter = " or ".join(f"Document_No eq '{po}'" for po in po_list)
    get_response = requests.get(f"{odata_base}/Purchase_Order_Line_Excel?$filter={odata_filter}&$select=Document_Type,Document_No,Line_No,No,Description,Quantity,Qty_to_Receive,Quantity_Received,Requested_Receipt_Date,Planned_Receipt_Date,Expected_Receipt_date,Inbound_Whse_Handling_Time", headers=BC_HEADERS, timeout=30)
    purlines = pd.DataFrame(get_response.json()["value"])
    purlines
    return odata_base, purlines


@app.cell
def _(DOWNLOADS_DIR, datetime, invoice_dict, mo, pd):
    # this whole cell will be replaced with the API call

    required_columns = ["Document No.", "Line No.", "Buy-from Vendor No.", "No.", "Expected Receipt Date", "Quantity", "Outstanding Quantity", "Qty. to Receive", "Requested Receipt Date", "Ship Date"]

    # look through downloads folder, find newest `Default*` file, check if it's the right config export, and pull into a df
    downloads = list(DOWNLOADS_DIR.glob("Default*.xlsx"))
    newest = max(downloads, key=lambda x: x.stat().st_mtime)
    today = datetime.today().date()
    if datetime.fromtimestamp(newest.stat().st_mtime).date() != today:
        print("Warning: no recent config pkg download found")
        print("Download fresh file and rerun this cell")
    purlines = pd.read_excel(newest, header=2)
    columns = purlines.columns.tolist()
    try:
        start = columns.index("Document No.")
        if columns[start:start + len(required_columns)] != required_columns:
            raise ValueError
    except ValueError:
        print(f"Warning: PURLINES download needed with {required_columns}")
        print("Download fresh file and rerun this cell")

    purlines = (
        purlines
        .assign(
            **{
                "Expected Receipt Date": lambda d: pd.to_datetime(d["Expected Receipt Date"]),
                "Ship Date": lambda d: pd.to_datetime(d["Ship Date"]),
                "Requested Receipt Date": lambda d: pd.to_datetime(d["Requested Receipt Date"])
            },
            po_item_key=lambda d: d["Document No."] + "|" + d["No."].str.replace("-", "", regex=False)
        )
    )

    purlines_confirmation = "Purlines loaded. \n\n"

    # check all invoice lines found in purlines file
    invoice_keys = set(invoice_dict)
    purlines_keys = set(purlines["po_item_key"])
    missing = invoice_keys - purlines_keys
    if missing:
        for po_item in missing:
            purlines_confirmation += (f"**WARNING** \n\nThese lines not found in purlines file. Either handle them manually or add to BC and rerun this cell. \n\n")
            purlines_confirmation += (f"{po_item} — {invoice_dict[po_item]} \n\n")


    mo.md(purlines_confirmation)
    return newest, purlines


@app.cell
def _(BC_HEADERS, odata_base, requests):
    etag = 'W/"JzIwOzE2Nzk5NjYxMTUzODUzMjcyNjcwMTswMDsn"'

    patch_headers = {**BC_HEADERS, "Content-Type": "application/json", "If-Match": etag}

    test = requests.patch(
        f"{odata_base}/Purchase_Order_Line_Excel(Document_Type='Order',Document_No='PO0008842',Line_No=10000)",
        headers=patch_headers,
        json={"Qty_to_Receive": 0},
        timeout=30,
    )

    test.status_code, test.text
    return


@app.cell
def _(
    ATLCA_BUFFER_DAYS,
    CAMEL_BUFFER_DAYS,
    pd,
    po_list,
    purlines,
    shipment_date,
):
    # filter to only lines shipped and/or past-due

    shipped_pos = purlines["Document No."].isin(po_list)

    atlca_past_due = (
        (purlines["Buy-from Vendor No."] == "ATLCA")
        & (purlines["Requested Receipt Date"] < shipment_date + pd.Timedelta(days=ATLCA_BUFFER_DAYS))
        & (purlines["Outstanding Quantity"] > 0)
    )
    camel_past_due = (
        (purlines["Buy-from Vendor No."] == "CAMEL")
        & (purlines["Requested Receipt Date"] < shipment_date + pd.Timedelta(days=CAMEL_BUFFER_DAYS))
        & (purlines["Outstanding Quantity"] > 0)
    )

    filtered_purlines = (
        purlines
        .assign(past_due=atlca_past_due | camel_past_due)
        .loc[lambda d: shipped_pos | d["past_due"]]
        .reset_index(drop=True)
    )

    # filtered_purlines
    return (filtered_purlines,)


@app.cell
def _(mo):
    # will still need button for API version
    # should only patch back when confirmed all lines are good

    open_file_button = mo.ui.run_button(label="Open files for upload")
    open_file_button
    return (open_file_button,)


@app.cell
def _(
    ATLCA_BUFFER_DAYS,
    CAMEL_BUFFER_DAYS,
    TRANSIT_DAYS,
    filtered_purlines,
    invoice_dict,
    mo,
    newest,
    open_file_button,
    os,
    pd,
):
    def fill_qties(group, remaining):
        group["Qty. to Receive"] = 0 # zero everything to start so that when the loop breaks with open lines remaining, those are already zeroed
        open_lines = group[group["Outstanding Quantity"]>0].sort_values("Line No.")
        if open_lines.empty:
            group.loc[group["Line No."].idxmax(), "Qty. to Receive"] = remaining
        else:
            for idx, line in open_lines.iterrows():
                if remaining > line["Outstanding Quantity"]:
                    group.loc[idx, "Qty. to Receive"] = line["Outstanding Quantity"]
                    remaining = remaining - line["Outstanding Quantity"]
                else:
                    group.loc[idx, "Qty. to Receive"] = remaining
                    remaining = 0
                    break
            if remaining > 0:
                group.loc[open_lines.index[-1], "Qty. to Receive"] += remaining
        return group

    def update_date(df):
        is_camel = df["Buy-from Vendor No."] == "CAMEL"
        df.loc[is_camel, "Ship Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=CAMEL_BUFFER_DAYS)
        df.loc[is_camel, "Expected Receipt Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=CAMEL_BUFFER_DAYS + TRANSIT_DAYS)
        df.loc[~is_camel, "Ship Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=ATLCA_BUFFER_DAYS)
        df.loc[~is_camel, "Expected Receipt Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=ATLCA_BUFFER_DAYS + TRANSIT_DAYS) # have to explicitly write Expected Receipt Date as programmatic update doesn't trigger recalc
        return df

    def update_purlines(invoice_dict, filtered_purlines): # dict, df
        result = filtered_purlines.copy()
        result["Qty. to Receive"] = 0 # zero everything first

        shipped = result["po_item_key"].isin(invoice_dict) # PO-items on this container
        for po_item_key, lines in result[shipped].groupby("po_item_key"):
            qty_shipped = invoice_dict[po_item_key]
            filled = fill_qties(lines, qty_shipped)
            result.loc[filled.index, "Qty. to Receive"] = filled["Qty. to Receive"]

        past_due = result["past_due"]
        result.loc[past_due] = update_date(result.loc[past_due].copy())

        return result

    output = update_purlines(invoice_dict, filtered_purlines)

    if open_file_button.value:
        output.to_excel("output.xlsx", index=False)
        os.startfile("output.xlsx")
        os.startfile(str(newest))
        mo.md("Opening files for config pkg upload...")
    return (output,)


@app.cell
def _(mo):
    open_po_button = mo.ui.run_button(label="Config pkg uploaded? Press this button to go to PO list")
    open_po_button
    return (open_po_button,)


@app.cell(hide_code=True)
def _(BC_BASE, filter_string, open_po_button, webbrowser):
    if open_po_button.value:
        bc_url = f"{BC_BASE}&page=9307&filter='No.' IS '{filter_string}'"
        webbrowser.open(bc_url)
    return


@app.cell(hide_code=True)
def _(camel_invoice, mo, time):
    blocks = []
    display_df = camel_invoice.groupby(["po", "item"])["qty_shipped"].sum().reset_index()
    for po_num, items_df in display_df.groupby("po"):
        ...
        rows = ""
        for _, q in items_df.iterrows():
            rows += f"<tr><td>{q['item']}</td><td style='text-align:right'>{q['qty_shipped']}</td></tr>"
        po_table = f"<table style='border:none;border-collapse:collapse'>{rows}</table>"
        blocks.append(f"<details key='{po_num}-{time.time()}' open><summary>{po_num}</summary>{po_table}</details>")

    style = "<style>details { margin: 0; } details table { margin: 0; } details summary { padding: 0; }</style>"

    mo.md(style + "\n".join(blocks))
    return


@app.cell(hide_code=True)
def _(output):
    transfer = (
        output[output["Qty. to Receive"] > 0]
        .groupby("No.")["Qty. to Receive"]
        .sum()
        .sort_index()
    )
    transfer
    return (transfer,)


@app.cell(hide_code=True)
def _(container, mo, pyperclip, transfer):
    item_list = "\n".join(str(item) for item in transfer.index)
    copy_items_button = mo.ui.button(label="item list", on_click=lambda _: pyperclip.copy(item_list))

    transfer_container = f"CAMEL {container}"
    copy_container_button = mo.ui.button(label=transfer_container, on_click=lambda _: pyperclip.copy(transfer_container))

    transfer_number = None
    transfer_number_input = mo.ui.text(placeholder="Transfer order number")

    mo.md(f"**Copy container number** — {copy_container_button} \n\n**Paste transfer number** — {transfer_number_input} \n\n **Copy item list** — {copy_items_button}")
    return transfer_container, transfer_number_input


@app.cell(hide_code=True)
def _(
    TRANSIT_DIR,
    files,
    mo,
    shipment_date,
    transfer_container,
    transfer_number_input,
):
    filing_display = "Files not yet saved to In Transit folder"
    if transfer_number_input.value: 
        folder_name = f"{shipment_date.strftime('%y-%m-%d')} {transfer_container} {transfer_number_input.value}"
        dest = TRANSIT_DIR / folder_name
        dest.mkdir(exist_ok=True)
        for file in files.value:
            (dest / file.name).write_bytes(file.contents)
        filing_display = "Files saved to In Transit folder"

    mo.md(filing_display)
    return


if __name__ == "__main__":
    app.run()
