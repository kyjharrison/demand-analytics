import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    #TODO check 06 is empty afterwards
    return


@app.cell
def _():
    # TODO add lines to adjust
    return


@app.cell
def _():
    # TODO add lines to close
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


@app.cell
def _():
    #TODO add overreceipt guard
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import io
    import json
    import requests
    import sys
    import time
    import webbrowser

    from datetime import datetime
    from pathlib import Path

    import pandas as pd
    import pdfplumber
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
        TRANSIT_DAYS,
        TRANSIT_DIR,
        build_bc_odata_base_url,
        io,
        mo,
        pd,
        pdfplumber,
        re,
        requests,
        time,
        webbrowser,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Process container
    """)
    return


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
def _(BC_HEADERS, container, mo, odata_base, requests):
    # check if container already exists in transfer order list

    vendor = "CAMEL"
    transfer_container = f"{vendor} {container}"

    container_check_warning = ""
    existing = requests.get(
        f"{odata_base}/Transfer_Order_Excel?$filter=CGWContainerNo eq '{transfer_container}'&$select=No,CGWContainerNo",
        headers=BC_HEADERS, timeout=30,
    ).json()
    if existing["value"]:
        container_check_warning = f"**WARNING** \n\n Transfer order {existing['value'][0]['No']} already exists for {transfer_container}. \n\nPlease check if this container has already been processed."
    mo.md(container_check_warning)
    return existing, transfer_container


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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def _(
    BC_CONFIG,
    BC_HEADERS,
    build_bc_odata_base_url,
    invoice_dict,
    mo,
    pd,
    po_list,
    requests,
):
    odata_base = build_bc_odata_base_url(BC_CONFIG)

    # GET all PO headers from these invoices in order to update the Posting Date 
    inv_header_filter = " or ".join(f"No eq '{po}'" for po in po_list)
    get_header_response = requests.get(f"{odata_base}/Purchase_Order_Excel?$filter={inv_header_filter}&$select=Document_Type,No,Posting_Date,Status", headers=BC_HEADERS, timeout=30)
    bc_inv_headers = pd.DataFrame(get_header_response.json()["value"])
    bc_inv_headers

    # GET all lines from POs on this invoice
    # all lines must be pulled, not just the items shipped, because Qty_to_Receive must be zeroed out for items not shipped
    inv_line_filter = " or ".join(f"Document_No eq '{po}'" for po in po_list)
    get_line_response = requests.get(f"{odata_base}/Purchase_Order_Line_Excel?$filter={inv_line_filter}&$select=Document_Type,Document_No,Line_No,No,Description,Quantity,Quantity_Received,Qty_to_Receive", headers=BC_HEADERS, timeout=30)
    bc_inv_lines = (
        pd.DataFrame(get_line_response.json()["value"])
        .assign(Outstanding_Quantity=lambda d: d["Quantity"] - d["Quantity_Received"])
        .assign(New_Qty_to_Receive=0)
        .assign(po_item_key=lambda d: d["Document_No"] + "|" + d["No"].str.replace("-", "", regex=False))
    )
    bc_inv_lines

    # data validation and confirmation
    bc_inv_get_confirmation = "Invoice POs loaded from BC. \n\n"

    # check all lines from the invoices are present in the data pull and alert user if not
    invoice_keys = set(invoice_dict)
    bc_inv_lines_keys = set(bc_inv_lines["po_item_key"])
    missing = invoice_keys - bc_inv_lines_keys
    if missing:
        bc_inv_get_confirmation += (f"**WARNING** \n\nThese lines not found in BC. Either handle them manually or add to BC and rerun this cell.")
        for po_item in missing:
            bc_inv_get_confirmation += f"  \n{po_item} — {invoice_dict[po_item]}"

    # check all POs released and alert user if not
    not_released = bc_inv_headers[bc_inv_headers["Status"] != "Released"]
    if not not_released.empty:
        bc_inv_get_confirmation += f"**WARNING** \n\n These POs are not Released and cannot be posted against. \n\n Get them released and rerun this cell."
        for _, header_row in not_released.iterrows():
            bc_inv_get_confirmation += f"  \n{header_row['No']} status is {header_row['Status']}"

    mo.md(bc_inv_get_confirmation)
    return bc_inv_headers, bc_inv_lines, missing, odata_base


@app.cell(hide_code=True)
def _(bc_inv_headers, bc_inv_lines, invoice_dict, pd, shipment_date):
    # logic for how to distribute a single PO-item's shipped qty across multiple PO lines
    # gets called within update_purlines
    def fill_qties(group, remaining):
        group["New_Qty_to_Receive"] = 0 # zero everything to start so that when the loop breaks with open lines remaining, those are already zeroed
        open_lines = group[group["Outstanding_Quantity"]>0].sort_values("Line_No")
        if open_lines.empty:
            group.loc[group["Line_No"].idxmax(), "New_Qty_to_Receive"] = remaining
        else:
            for idx, line in open_lines.iterrows():
                if remaining > line["Outstanding_Quantity"]:
                    group.loc[idx, "New_Qty_to_Receive"] = line["Outstanding_Quantity"]
                    remaining = remaining - line["Outstanding_Quantity"]
                else:
                    group.loc[idx, "New_Qty_to_Receive"] = remaining
                    remaining = 0
                    break
            if remaining > 0:
                group.loc[open_lines.index[-1], "New_Qty_to_Receive"] += remaining
        return group

    # function that works through the PO_items on this container and call fill_qties to distribute the qties
    def update_purlines(invoice_dict, filtered_purlines): 
        result = bc_inv_lines.copy()
        shipped = result["po_item_key"].isin(invoice_dict) # PO-items on this container
        for po_item_key, lines in result[shipped].groupby("po_item_key"):
            qty_shipped = invoice_dict[po_item_key]
            filled = fill_qties(lines, qty_shipped)
            result.loc[filled.index, "New_Qty_to_Receive"] = filled["New_Qty_to_Receive"]
        return result

    # if shipment_date in previous month, post on first day of current month instead
    today = pd.Timestamp.today().normalize()
    if shipment_date.month != today.month:
        posting_date = today.replace(day=1).strftime("%Y-%m-%d")
    else:
        posting_date = shipment_date.strftime("%Y-%m-%d")
    patch_inv_headers = (
        bc_inv_headers
        .assign(Posting_Date=posting_date)
    )
    patch_inv_headers

    patch_inv_lines = update_purlines(invoice_dict, bc_inv_lines)

    patch_inv_lines[["Document_No",   "No", "Description", "Outstanding_Quantity","Qty_to_Receive", "New_Qty_to_Receive", "Quantity", "Quantity_Received",  "Line_No","po_item_key", "@odata.etag"]]
    return patch_inv_headers, patch_inv_lines, posting_date


@app.cell(hide_code=True)
def _(mo):
    # keep API patch behind button confirmation

    update_bc_inv_button = mo.ui.run_button(label="Run")
    mo.md(f"Update BC? \n\n(This will update Posting Dates, Qty to Receive, and also create a transfer order for the shipment.) \n\n {update_bc_inv_button}")
    return (update_bc_inv_button,)


@app.cell(hide_code=True)
def _(
    BC_HEADERS,
    mo,
    odata_base,
    patch_inv_headers,
    patch_inv_lines,
    requests,
    update_bc_inv_button,
):
    bc_inv_patch_confirmation = "Posting dates and qties not yet updated in BC"

    if update_bc_inv_button.value:
        errors = []

        # update Posting_Date on PO headers
        for _, patch_header_row in patch_inv_headers.iterrows():
            patch_header_response = requests.patch(
                f"{odata_base}/Purchase_Order_Excel(Document_Type='{patch_header_row['Document_Type']}',No='{patch_header_row['No']}')",
                headers={**BC_HEADERS, "Content-Type": "application/json", "If-Match": patch_header_row["@odata.etag"]},
                json={"Posting_Date": patch_header_row["Posting_Date"]},
                timeout=30,
            )
            if patch_header_response.status_code != 200:
                errors.append(f"{patch_header_row['No']}: {patch_header_response.status_code} — {patch_header_response.text}")

        # update Qty_to_Receive on PO lines
        for _, patch_line_row in patch_inv_lines.iterrows():
            if patch_line_row["Qty_to_Receive"] == patch_line_row["New_Qty_to_Receive"]:
                continue
            patch_inv_line_response = requests.patch(
                f"{odata_base}/Purchase_Order_Line_Excel(Document_Type='{patch_line_row['Document_Type']}',Document_No='{patch_line_row['Document_No']}',Line_No={patch_line_row['Line_No']})",
                headers={**BC_HEADERS, "Content-Type": "application/json", "If-Match": patch_line_row["@odata.etag"]},
                json={"Qty_to_Receive": patch_line_row["New_Qty_to_Receive"]},
                timeout=30,
            )
            if patch_inv_line_response.status_code != 200:
                errors.append(f"{patch_line_row['Document_No']}: {patch_inv_line_response.status_code} — {patch_inv_line_response.text}")

        if errors:
            bc_inv_patch_confirmation = "**ERRORS:**\n\n" + "\n\n".join(errors)
        else:
            bc_inv_patch_confirmation = "All updates applied."

    mo.md(bc_inv_patch_confirmation)
    return


@app.cell(hide_code=True)
def _(mo):
    open_bc_po_rcv_button = mo.ui.run_button(label="Open BC")
    mo.md(f"Please verify qties against the list below and post receipts in BC \n\n {open_bc_po_rcv_button}")
    return (open_bc_po_rcv_button,)


@app.cell(hide_code=True)
def _(BC_BASE, filter_string, open_bc_po_rcv_button, webbrowser):
    if open_bc_po_rcv_button.value:
        bc_po_rcv_url = f"{BC_BASE}&page=9307&filter='No.' IS '{filter_string}'"
        webbrowser.open(bc_po_rcv_url)
    return


@app.cell(hide_code=True)
def _(camel_invoice, mo, open_bc_po_rcv_button, time):
    # display shipped items and qties for verification
    blocks = []
    if open_bc_po_rcv_button.value:
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
def _(
    BC_HEADERS,
    existing,
    mo,
    odata_base,
    pd,
    posting_date,
    requests,
    shipment_date,
    transfer_container,
    update_bc_inv_button,
):
    transfer_header_confirmation = "No transfer created yet."

    if update_bc_inv_button.value:
        if existing["value"]:
            transfer_no = existing['value'][0]['No']
            transfer_header_confirmation = f"Transfer order already exists for {transfer_container}. Please double check."
        else:
            shipping_time = "6W"
            receipt_date = (shipment_date + pd.Timedelta(weeks=int(shipping_time.replace("W", "")))).strftime("%Y-%m-%d")
            transfer_header_post = requests.post(
                f"{odata_base}/Transfer_Order_Excel",
                headers={**BC_HEADERS, "Content-Type": "application/json"},
                json={
                    "Transfer_from_Code": "06",
                    "Transfer_to_Code": "01",
                    "Posting_Date": posting_date,
                    "CGWContainerNo": transfer_container,
                    "Shipment_Date": shipment_date.strftime("%Y-%m-%d"),
                    "Shipping_Time": shipping_time,
                    "Receipt_Date": receipt_date,
                },
                timeout=30,
            )
            transfer_no = transfer_header_post.json()["No"]
            transfer_header_confirmation = f"Transfer order {transfer_no} created"

    mo.md(transfer_header_confirmation)
    return (transfer_no,)


@app.cell(hide_code=True)
def _(patch_inv_lines):
    # aggregate final list of items that were received in BC for transfer
    transfer = (
        patch_inv_lines[patch_inv_lines["New_Qty_to_Receive"] > 0]
        .groupby("No")["New_Qty_to_Receive"]
        .sum()
        .astype(int)
        .sort_index()
    )
    transfer
    return (transfer,)


@app.cell(hide_code=True)
def _(invoice_dict, missing):
    missing_reminder = None
    if missing:
        missing_reminder = "**Reminder — these items were not found in BC and are not included in the transfer:**\n\n"
        missing_reminder += "\n".join(f"{po_item} — {invoice_dict[po_item]}" for po_item in missing)
    missing_reminder
    return


@app.cell(hide_code=True)
def _(
    BC_HEADERS,
    existing,
    mo,
    odata_base,
    requests,
    transfer,
    transfer_no,
    update_bc_inv_button,
):
    transfer_line_confirmation = "No transfer order created yet."

    if update_bc_inv_button.value and not existing["value"]:
        transfer_line_errors = []

        for item_no, qty in transfer.items():

            # add item as new line on transfer order
            transfer_line_item = requests.post(
                f"{odata_base}/CGWTransferOrder",
                headers={**BC_HEADERS, "Content-Type": "application/json"},
                json={
                    "TransferOrderNumber": transfer_no,
                    "ItemNo": item_no,
                },
                timeout=30,
            )
            if transfer_line_item.status_code != 201:
                transfer_line_errors.append(f"{item_no}: {transfer_line_item.status_code} — {transfer_line_item.text}")
                continue
            line_no = transfer_line_item.json()["TransferOrderLineNumber"]

            # get etag and line number
            etag = requests.get(
            f"{odata_base}/CGWTransferOrder(TransferOrderNumber='{transfer_no}',TransferOrderLineNumber={line_no})",
            headers=BC_HEADERS, timeout=30,
        ).json()["@odata.etag"]

            # enter qty on transfer line 
            transfer_line_qty = requests.patch(
                f"{odata_base}/CGWTransferOrder(TransferOrderNumber='{transfer_no}',TransferOrderLineNumber={line_no})",
                headers={**BC_HEADERS, "Content-Type": "application/json", "If-Match": etag},
                json={"TransferOrderQty": int(qty)},
                timeout=30,
            )
            if transfer_line_qty.status_code != 200:
                transfer_line_errors.append(f"{item_no} qty: {transfer_line_qty.status_code} — {transfer_line_qty.text}")

        if transfer_line_errors:
            transfer_line_confirmation = "  \n".join(transfer_line_errors)
        else:
            transfer_line_confirmation = f"Transfer order {transfer_no} created in BC. Please review and ship in BC."

    mo.md(transfer_line_confirmation)
    return


@app.cell(hide_code=True)
def _(mo):
    open_transfer_order_button = mo.ui.run_button(label="Review transfer order")
    open_transfer_order_button
    return (open_transfer_order_button,)


@app.cell(hide_code=True)
def _(BC_BASE, open_transfer_order_button, transfer_no, webbrowser):
    if open_transfer_order_button.value:
        bc_transfer_url = f"{BC_BASE}&page=5740&filter='No.' IS '{transfer_no}'"
        webbrowser.open(bc_transfer_url)
    return


@app.cell(hide_code=True)
def _(
    TRANSIT_DIR,
    files,
    mo,
    open_transfer_order_button,
    shipment_date,
    transfer_container,
    transfer_no,
):
    filing_display = "Files not yet saved to In Transit folder"
    if open_transfer_order_button.value:
        folder_name = f"{shipment_date.strftime('%y-%m-%d')} {transfer_container} {transfer_no}"
        dest = TRANSIT_DIR / folder_name
        dest.mkdir(exist_ok=True)
        for file in files.value:
            (dest / file.name).write_bytes(file.contents)
        filing_display = "Files saved to In Transit folder"
    mo.md(filing_display)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Push back past-due lines
    """)
    return


@app.cell
def _(ATLCA_BUFFER_DAYS, CAMEL_BUFFER_DAYS, TRANSIT_DAYS, pd):
    # TODO past-due date push

    def update_date(df):
        is_camel = df["Buy-from Vendor No."] == "CAMEL"
        df.loc[is_camel, "Ship Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=CAMEL_BUFFER_DAYS)
        df.loc[is_camel, "Expected Receipt Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=CAMEL_BUFFER_DAYS + TRANSIT_DAYS)
        df.loc[~is_camel, "Ship Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=ATLCA_BUFFER_DAYS)
        df.loc[~is_camel, "Expected Receipt Date"] = pd.Timestamp.today().normalize() + pd.Timedelta(days=ATLCA_BUFFER_DAYS + TRANSIT_DAYS) # have to explicitly write Expected Receipt Date as programmatic update doesn't trigger recalc
        return df



    return


@app.cell
def _():

    # revisit this logic later for the past-due date push

    # Requested_Receipt_Date,Planned_Receipt_Date,Expected_Receipt_date,Inbound_Whse_Handling_Time

    # filter to only lines shipped and/or past-due

    # shipped_pos = purlines["Document No."].isin(po_list)

    # atlca_past_due = (
    #     (purlines["Buy-from Vendor No."] == "ATLCA")
    #     & (purlines["Requested Receipt Date"] < shipment_date + pd.Timedelta(days=ATLCA_BUFFER_DAYS))
    #     & (purlines["Outstanding_Quantity"] > 0)
    # )
    # camel_past_due = (
    #     (purlines["Buy-from Vendor No."] == "CAMEL")
    #     & (purlines["Requested Receipt Date"] < shipment_date + pd.Timedelta(days=CAMEL_BUFFER_DAYS))
    #     & (purlines["Outstanding_Quantity"] > 0)
    # )

    # filtered_purlines = (
    #     purlines
    #     .assign(past_due=atlca_past_due | camel_past_due)
    #     .loc[lambda d: shipped_pos | d["past_due"]]
    #     .reset_index(drop=True)
    # )

    # filtered_purlines
    return


if __name__ == "__main__":
    app.run()
