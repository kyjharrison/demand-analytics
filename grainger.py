import marimo

__generated_with = "0.23.14"
app = marimo.App(width="full")


@app.cell
def imports():
    import pandas as pd
    import sqlite3 as sql
    db = r"C:\Users\Ky.Harrison\OneDrive - CGW Abrasives\Demand Analytics\internal\clean-mirror\clean_mirror.db"
    return db, pd, sql


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    pull item master list from database
    """)
    return


@app.cell(hide_code=True)
def item_master_list(db, pd, sql):
    conn = sql.connect(db)
    items = pd.read_sql("SELECT Item, Description, product, LC FROM item", conn)
    items
    return conn, items


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    filter to flapdiscs
    """)
    return


@app.cell(hide_code=True)
def flapdiscs_only(items):
    flapdiscs = items[items["Product"] == "FLAPDISCS"].reset_index(drop=True)
    flapdiscs
    return (flapdiscs,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    pull current weights and dimensions from the Item Unit of Measure table
    """)
    return


@app.cell(hide_code=True)
def current_uom_in_system(flapdiscs, pd):
    cgw = pd.read_excel(r"C:\Users\Ky.Harrison\OneDrive - CGW Abrasives\Shared Documents\Edit-in-Excel\Item Units Of Measure.xlsx")
    cgw = cgw.rename(columns={"Item No.": "Item"})
    cgw["key"] = cgw["Item"] + "|" + cgw["Code"]
    cgw = cgw[cgw["Item"].isin(flapdiscs["Item"])].reset_index(drop=True)
    cgw 
    return (cgw,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Flap boxes
    """)
    return


@app.cell(hide_code=True)
def boxes_from_boms(conn, items, pd):
    boms = pd.read_sql("select item, line, component from boms where line IN (107, 109)", conn)
    boms = boms.merge(items[["Item", "Description"]], on="Item", how="left")
    boms
    return (boms,)


@app.cell(hide_code=True)
def box_receipt_lines_for_dimensions(boms, conn, pd):
    boxes = boms["Component"].unique().tolist()
    placeholders = ",".join("?" * len(boxes))
    query = f"SELECT * FROM item_ledger_entries WHERE item IN ({placeholders}) AND Document_Type = 'Purchase Receipt' AND Posting_Date < '2025-06-01'"
    ledger = pd.read_sql(query, conn, params=boxes)
    ledger
    return (ledger,)


@app.cell(hide_code=True)
def split_descriptions_into_dimensions(ledger, pd):
    dims = (ledger[["Item", "Description_2"]]
        .drop_duplicates()
        .sort_values("Item")
        .reset_index(drop=True)
           )
    dims["Description_2"] = dims["Description_2"].str.replace('"', '')
    dims[["Length", "Width", "Height"]] = dims["Description_2"].str.split(r"\s[Xx]\s", expand=True)
    dims[["Height", "remainder"]] = dims["Height"].str.split(" ", n=1, expand=True)
    dims["dimensions"] = dims["Length"] + dims["Width"] + dims["Height"]
    dims = pd.concat([
        dims[dims["dimensions"].isna()],
        dims[dims["dimensions"].notna()].drop_duplicates(subset=["Item", "dimensions"])
    ])
    dims = dims.sort_values("Item")
    dims = dims.drop(index=[2, 4,7, 6, 8, 11, 18, 25]).drop(columns=["remainder", "dimensions"])
    dims = dims.rename(columns={"Item": "Component"})
    dims.loc[dims["Component"] == '96025', ["Length", "Width", "Height"]] = ["4", "4", "6"]
    dims.loc[dims["Component"] == '96027', ["Length", "Width", "Height"]] = ["5-1/4", "5-1/4", "9"]
    dims = dims[dims["Component"] != '96026']
    dims = dims.reset_index(drop=True)
    dims
    return (dims,)


@app.cell(hide_code=True)
def pull_box_dims_onto_boms(boms, dims, flapdiscs, pd):
    flapdims = boms.merge(dims, on="Component", how="left")
    flapbox = flapdims[flapdims["Line"] == 107]
    flapbox["Code"] = "BX"
    flapcase = flapdims[flapdims["Line"] == 109]
    flapcase["Code"] = "CS"
    bom_dims = pd.concat([flapbox, flapcase]).reset_index(drop=True)
    bom_dims["key"] = bom_dims["Item"] + "|" + bom_dims["Code"]
    bom_dims = bom_dims[["Item", "Code", "Length", "Width", "Height", "key", "Component"]]
    bom_dims = bom_dims.merge(flapdiscs[["Item", "LC"]], on="Item", how="left")
    bom_dims
    # bom_dims.to_excel("dims.xlsx", index=False)
    return


@app.cell
def _():
    return


app._unparsable_cell(
    r"""
    uom_flaps = cgw[(cgw["Item"].isin(flapdiscs["Item"]))

    check = cgw[(cgw["Item"].isin(flapdiscs["Item"])) & (cgw["Code"] != "EA")] #filter cgw uom table to only flapdiscs bx and cs
    # check = check.merge(bom_dims, on="key", suffixes=("_uom", "_bom"), how="outer") # join with parsed bom_dim tables
    # comp = ["Width", "Length", "Height"]
    # for c in comp:
    #     check[f"{c}_match"] = check[f"{c}_uom"] == check[f"{c}_bom"]
    check = check[check["Weight"] != 0]
    check

    """,
    name="_"
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Grainger
    """)
    return


@app.cell
def _(pd):
    grainger = pd.read_excel(r"C:\Users\Ky.Harrison\OneDrive - CGW Abrasives\Demand Analytics\Abrasic MOQ_Packaging Updates 3-20-26 REVIEW 041426.xlsx", dtype={"Mfr Model No": str, "Supplier Stock No": str})
    grainger = grainger[["Mfr Model No", "Sales Status", "Uom Qty", "Current MOQ", "New MOQ", "Master Pack Qty", "Master Pack Length", "Master Pack Width", "Master Pack Height", "Master Pack Weight", "Ship Pack Qty", "Ship Pack Length", "Ship Pack Width", "Ship Pack Height", "Ship Pack Weight", "Sell Pack Qty", "Sell Pack Length", "Sell Pack Width", "Sell Pack Height", "Sell Pack Weight"]]
    grainger
    return (grainger,)


@app.cell
def _(cgw, flapdiscs, grainger):
    ea = cgw[cgw["Code"] == "EA"]
    ea = ea[ea["Item"].isin(grainger["Mfr Model No"])]
    ea = ea[ea["Item"].isin(flapdiscs["Item"])]
    ea = ea.merge(cgw[cgw["Code"] == "BX"], on="Item", how="left", suffixes=("_ea", "_bx"))
    ea = ea.merge(cgw[cgw["Code"] == "CS"], on="Item", how="left")
    ea 
    return


app._unparsable_cell(
    r"""
    case = grainger[["Mfr Model No", "Master Pack Qty", "Master Pack Length", "Master Pack Width", "Master Pack Height", "Master Pack Weight"]].copy()
    case.insert(1, "Code", "CS")
    case = case.rename(columns={"Mfr Model No": "Item No.", "Master Pack Qty": "Qty. per Unit of Measure", "Master Pack Width": "Width", "Master Pack Length": "Length","Master Pack Height": "Height", "Master Pack Weight": "Weight"]]})
    case
    """,
    name="_"
)


@app.cell
def _(grainger):
    box = grainger[["Mfr Model No", "Ship Pack Qty", "Ship Pack Length", "Ship Pack Width", "Ship Pack Height", "Ship Pack Weight"]].copy()
    box.insert(1, "Code", "BX")
    box = box.rename(columns={"Mfr Model No": "Item No.", "Ship Pack Qty": "Qty. per Unit of Measure", "Ship Pack Width": "Width", "Ship Pack Length": "Length", "Ship Pack Height": "Height", "Ship Pack Weight": "Weight"})
    box
    return (box,)


@app.cell(hide_code=True)
def _(grainger):
    each = grainger[["Mfr Model No", "Sell Pack Qty", "Sell Pack Length", "Sell Pack Width", "Sell Pack Height", "Sell Pack Weight"]].copy()
    each.insert(1, "Code", "EA")
    each = each.rename(columns={"Mfr Model No": "Item No.", "Sell Pack Qty": "Qty. per Unit of Measure", "Sell Pack Width": "Width", "Sell Pack Length": "Length", "Sell Pack Height": "Height", "Sell Pack Weight": "Weight"})
    each
    return (each,)


@app.cell
def _(box, case, each, pd):
    clean = pd.concat([case, box, each]).reset_index(drop=True)
    clean["key"] = clean["Item No."] + "|" + clean["Code"]
    clean
    return (clean,)


@app.cell
def _(cgw):
    blank = (cgw.groupby("Code")[["key", "Width", "Length", "Height", "Weight"]] .apply(lambda x: (x == 0).sum()))
    blank
    return


@app.cell
def _(cgw, clean):
    missing = clean[~clean["key"].isin(cgw["key"])]
    missing.groupby("Code").size()
    return


@app.cell
def _(cgw, clean):
    merged = clean.merge(cgw, on="key", suffixes=("_gr", "_cg"))
    cols = ["Width", "Length", "Height", "Weight"]
    for col in cols:
        merged[f"{col}_match"] = merged[f"{col}_gr"] == merged[f"{col}_cg"]
    merged["all_match"] = merged[[f"{col}_match" for col in cols]].all(axis=1)
    merged[~merged["all_match"]]
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
