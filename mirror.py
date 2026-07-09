import requests
import sys
import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
import logging
from logging.handlers import TimedRotatingFileHandler

sys.path.insert(0, str(Path(__file__).parent.parent / "internal/bc-mirror"))
from bc_keyvault_auth import build_bc_api_base_url, build_bc_odata_base_url, get_bc_connection
from clean_tables.py import CLEAN_TABLES

BC_CONFIG, BC_HEADERS = get_bc_connection()

with open(Path(__file__).parent.parent / "internal/config.json") as f:
    config = json.load(f)

CONN_RAW = sqlite3.connect(config["DB_RAW"])
CONN_CLEAN = sqlite3.connect(config["DB_CLEAN"])

handler = TimedRotatingFileHandler(
    Path(__file__).parent.parent / "logs/mirror_refresh.log",
    when="midnight",
    backupCount=14,
)

handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])

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
        response = requests.get(f"{build_bc_api_base_url(BC_CONFIG)}/{endpoint}", headers=BC_HEADERS)
    elif api_type == "odata":
        response = requests.get(f"{build_bc_odata_base_url(BC_CONFIG)}/{endpoint}", headers=BC_HEADERS)
    else:
        logging.error('api_type must be defined as "base" or "odata"')
        sys.exit(1)
    if response.ok:
        return response
    else:
        logging.error(f"{endpoint} returned {response.status_code}: {response.text}")
        sys.exit(1)

def initialize_table(api_type, refresh_mode, endpoint, id_column, secondary_id=None, tertiary_id=None, watermark_column=None, watermark_type=None, table_filter=None):
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
        "table_filter": table_filter
        }
    with open(Path(config["SCHEMA_DIR"])/ f"{endpoint}.json", "w") as f:
        json.dump(schema, f, indent=2)

def refresh_table(schema): 
    
    start = datetime.now()

    endpoint = schema["endpoint"]
    api_type = schema["api_type"]
    refresh_mode = schema.get("refresh_mode")
    watermark_column = schema["watermark_column"]
    watermark_type = schema["watermark_type"]
    table_filter = schema.get("table_filter")

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
            logging.error(f"Schema must define watermark_type. Please check {endpoint}.json and try again.")
            sys.exit(1)
    elif table_filter:
        data, next_link = parse_response(call_api(f"{endpoint}?$filter={table_filter}", api_type))
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
            data, next_link = parse_response(requests.get(next_link, headers=BC_HEADERS))
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
    for table, query in CLEAN_TABLES.items():
        table_start = datetime.now()
        CONN_CLEAN.execute(f"DROP TABLE IF EXISTS {table}")
        CONN_CLEAN.execute(f"CREATE TABLE {table} AS {query}")
        logging.info(f"{table} refreshed in {datetime.now() - table_start}")
    CONN_CLEAN.commit()
    logging.info(f"clean_mirror.db rebuilt in {datetime.now() - start}")


if __name__ == "__main__":

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
        new.add_argument("--table_filter") # DO NOT COMBINE WITH WATERMARK

        refresh = subparsers.add_parser("refresh")
        refresh.add_argument("--endpoint")

        args = parser.parse_args()

        if args.mode == "test": 
            top = parse_response(call_api(args.endpoint, args.api_type))
            for line in top[0]:
                print(json.dumps(line))

        if args.mode == "new": 
            initialize_table(args.api_type, args.refresh_mode, args.endpoint, args.id_column, args.secondary_id, args.tertiary_id, args.watermark_column, args.watermark_type, args.table_filter) 

        if args.mode == "refresh":  
            if args.endpoint:
                with open(Path(config["SCHEMA_DIR"]) / f"{args.endpoint}.json") as f:
                    schema = json.load(f)
                refresh_table(schema)
            else:
                for file in Path(config["SCHEMA_DIR"]).glob("*.json"):
                    try:    
                        with open(file) as f:
                            schema = json.load(f)
                            refresh_table(schema)
                    except Exception as e:
                        logging.error(f"{file.stem} failed: {e}", exc_info=True)
                        logging.error(e)
        
        logging.info(f"BC refresh completed in {datetime.now() - start}")

        build_clean_mirror()

        logging.info(f"Full refresh completed in {datetime.now() - start}")
    
    except Exception as e:
        logging.critical(f"Script crashed: {e}", exc_info=True)
        sys.exit(1)