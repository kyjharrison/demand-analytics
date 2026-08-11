import requests
import sys
import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
import logging
from logging.handlers import TimedRotatingFileHandler
from bc_keyvault_auth import build_bc_api_base_url, build_bc_odata_base_url, get_bc_connection

sys.path.insert(0, str(Path(__file__).parent.parent / "alerts"))
from error_alert import send_alert

# set up logger
handler = TimedRotatingFileHandler(
    Path(__file__).parent.parent / "logs/mirror_refresh.log",
    when="midnight",
    backupCount=10,
)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])

# exit if outside business hours
now = datetime.now()
if now.weekday() >= 5 or not (6 <= now.hour < 20):
    logging.info("Script triggered outside working hours. Exiting...")
    sys.exit(0)


BC_CONFIG, BC_HEADERS = get_bc_connection()

with open(Path(__file__).parent.parent / "config.json") as f:
    config = json.load(f)

MIRROR_DIR = Path(config["MIRROR_DIR"])

SCHEMA_RAW = MIRROR_DIR / "schema"
CONN_RAW = sqlite3.connect(MIRROR_DIR / "bc_mirror.db")

SQL_CLEAN = MIRROR_DIR / "sql"
CONN_CLEAN = sqlite3.connect(MIRROR_DIR / "clean_mirror.db")

TIMEOUT = 90

def parse_response(response):
    data_raw = response.json()
    data = [{key: value for key, value in record.items()
             if not key.startswith("@")}
             for record in data_raw["value"]]
    next_link = data_raw.get("@odata.nextLink")
    return data, next_link

def call_api(endpoint, api_type):
    logging.info(f"Contacting server for endpoint: {endpoint} . . . ")
    if api_type == "base":
        response = requests.get(f"{build_bc_api_base_url(BC_CONFIG)}/{endpoint}", headers=BC_HEADERS, timeout=TIMEOUT)
    elif api_type == "odata":
        response = requests.get(f"{build_bc_odata_base_url(BC_CONFIG)}/{endpoint}", headers=BC_HEADERS, timeout=TIMEOUT)
    else:
        logging.error('api_type must be defined as "base" or "odata"')
        sys.exit(1)
    if response.ok:
        return response
    else:
        raise requests.HTTPError(f"{endpoint} returned {response.status_code}: {response.text}") # raise error so that the per-endpoint try/except can catch it

def initialize_table(api_type, refresh_mode, endpoint, id_column, secondary_id=None, tertiary_id=None, watermark_column=None, watermark_type=None, query_param=None):
    if query_param:
        data, _ = parse_response(call_api(f"{endpoint}?{query_param}&$top=1", api_type))
    else:
        data, _ = parse_response(call_api(f"{endpoint}?$top=1", api_type))
    keys = data[0].keys()
    if tertiary_id:
        fields = ", ".join(keys) + f", PRIMARY KEY ({id_column}, {secondary_id}, {tertiary_id})"
    elif secondary_id:
        fields = ", ".join(keys) + f", PRIMARY KEY ({id_column}, {secondary_id})"
    else:
        fields = ", ".join([k + " PRIMARY KEY" if k == id_column else k for k in keys])
    CONN_RAW.execute(f"CREATE TABLE IF NOT EXISTS {endpoint} ({fields})")
    schema = {
        "endpoint": endpoint, 
        "api_type": api_type, # base | odata
        "refresh_mode": refresh_mode, # upsert | truncate
        "watermark_column": watermark_column, # column name
        "watermark_type": watermark_type, # string | date_integer
        "id_column": id_column, 
        "secondary_id": secondary_id,
        "tertiary_id": tertiary_id,
        "query_param": query_param
        }
    with open(SCHEMA_RAW/ f"{endpoint}.json", "w") as f:
        json.dump(schema, f, indent=2)

def refresh_table(schema): 
    
    start = datetime.now()

    endpoint = schema["endpoint"]
    api_type = schema["api_type"]
    refresh_mode = schema.get("refresh_mode")
    watermark_column = schema["watermark_column"]
    watermark_type = schema["watermark_type"]
    query_param = schema.get("query_param")

    watermark = None
    if watermark_column:
        check_watermark = CONN_RAW.execute(f"SELECT latest_diff FROM watermark WHERE endpoint = '{endpoint}'").fetchone()
        watermark = check_watermark[0] if check_watermark else None

    if watermark:
        if watermark_type == "date_integer":
            data, next_link = parse_response(call_api(f"{endpoint}?$filter={watermark_column} ge {watermark}", api_type))
        elif watermark_type == "string":
            data, next_link = parse_response(call_api(f"{endpoint}?$filter={watermark_column} ge '{watermark}'", api_type))
        else:
            raise ValueError(f"Invalid watermark_type in {endpoint}.json. Expected 'date_integer' or 'string'.")
    elif query_param:
        data, next_link = parse_response(call_api(f"{endpoint}?{query_param}", api_type))
    else:
        data, next_link = parse_response(call_api(endpoint, api_type))
    keys = data[0].keys()
    number = len(keys)
    fields = ", ".join(keys)

    if refresh_mode == "truncate":
        CONN_RAW.execute(f"DELETE FROM {endpoint}")
        CONN_RAW.commit()

    i = 0
    count = 0
    while True:
        i = i + 1
        records = [tuple(record.values()) for record in data]
        count = count + len(records)
        CONN_RAW.executemany(f"INSERT OR REPLACE INTO {endpoint} ({fields}) VALUES ({', '.join('?' * number)})", records)
        CONN_RAW.commit()
        logging.info(f"{endpoint} written to file — page {i}")
        if next_link:
            data, next_link = parse_response(requests.get(next_link, headers=BC_HEADERS, timeout=TIMEOUT))
            continue
        else:
            break
    timestamp = datetime.now().isoformat()

    if watermark_column:
        watermark = CONN_RAW.execute(f"SELECT MAX({watermark_column}) FROM {endpoint}").fetchone()[0]
    values = (endpoint, watermark, timestamp)
    CONN_RAW.execute("INSERT OR REPLACE INTO watermark (endpoint, latest_diff, last_refreshed) VALUES (?, ?, ?)", values)
    CONN_RAW.commit()
    logging.info(f"{endpoint} refreshed: {count} records updated in {datetime.now() - start}")

def build_clean_mirror():
    start = datetime.now()
    CONN_CLEAN.execute("ATTACH DATABASE ? AS raw", (str(MIRROR_DIR / "bc_mirror.db"),)) # can't use CONN_RAW because sqlite expects a string filepath not a connection object
    clean_tables = [ 
        "bin_contents.sql",
        "boms.sql",
        "item_ledger_entries.sql",
        "items.sql",
        "posted_sales_invoice_lines.sql",
        "purchase_lines.sql",
        "sales_lines.sql",
        "transfer_lines.sql",
        
        "skus.sql", # must happen last, depends on item_ledger_entries, sales_lines, purchase_lines, and transfer_lines
    ]
    for filename in clean_tables:
        p = SQL_CLEAN / filename 
        table_start = datetime.now()
        CONN_CLEAN.executescript(p.read_text())
        logging.info(f"{p.stem} refreshed in {datetime.now() - table_start}")
    CONN_CLEAN.execute("DETACH DATABASE raw")
    logging.info(f"clean_mirror.db refreshed in {datetime.now() - start}")

if __name__ == "__main__":

    errors = []

    try:
        start = datetime.now()

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="mode")

        test = subparsers.add_parser("test")
        test.add_argument("--api_type", required=True)
        test.add_argument("--endpoint", required=True)

        new = subparsers.add_parser("new")
        new.add_argument("--api_type", required=True)
        new.add_argument("--refresh_mode", required=True)
        new.add_argument("--endpoint", required=True)
        new.add_argument("--id_column", required=True)
        new.add_argument("--secondary_id")
        new.add_argument("--tertiary_id")
        new.add_argument("--watermark_column") # omit for full refresh every time
        new.add_argument("--watermark_type") # omit for full refresh every time
        new.add_argument("--query_param") # DO NOT COMBINE WITH WATERMARK

        refresh = subparsers.add_parser("refresh")
        refresh.add_argument("--endpoint")

        clean = subparsers.add_parser("clean")
        
        args = parser.parse_args()

        if args.mode == "test": 
            top = parse_response(call_api(args.endpoint, args.api_type))
            for line in top[0]:
                print(json.dumps(line))

        if args.mode == "new": 
            initialize_table(args.api_type, args.refresh_mode, args.endpoint, args.id_column, args.secondary_id, args.tertiary_id, args.watermark_column, args.watermark_type, args.query_param) 

        if args.mode == "clean":
            build_clean_mirror()

        if args.mode == "refresh":  
            if args.endpoint:
                with open(SCHEMA_RAW / f"{args.endpoint}.json") as f:
                    schema = json.load(f)
                refresh_table(schema)
            else:
                for file in SCHEMA_RAW.glob("*.json"):
                    try:    
                        with open(file) as f:
                            schema = json.load(f)
                            refresh_table(schema)
                    except Exception as e:
                        logging.error(f"{file.stem} failed: {e}", exc_info=True)
                        errors.append(f"{file.stem}: {e}")
            logging.info(f"bc_mirror.db refreshed in {datetime.now() - start}")
            build_clean_mirror()
            logging.info(f"Full refresh completed in {datetime.now() - start}")
    
    except Exception as e:
        logging.critical(f"Script crashed: {e}", exc_info=True)
        errors.append(e)

    finally:
        if errors:
            message = "\n\n".join(str(e) for e in errors)
            send_alert(f"REFRESH — {len(errors)} errors", message)
    