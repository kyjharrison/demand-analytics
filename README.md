# Demand Analytics

Demand analysis tools for a local SQLite mirror of Dynamics 365 Business Central

## About

Got tired of clicking around the Business Central frontend UI, waiting endlessly for tables to download to Excel, and then manually joining them over and over. So I taught myself Python and SQL. 

### mirror.py

This script is the core of everything. Business Central doesn't expose the ERP data for direct SQL querying, so this hits the Odata endpoints and downloads to a local SQLite file. There's a `watermark` table that logs the latest record seen on each table, and only pulls the new ones. This keeps each refresh light and fast. 

### sales_history.py

BC's built in Sales History report takes a starting date and a period length and returns 8 periods — 8 months, 8 days, 8 years, however you like. Why 8? No idea. All I know is it won't give me the one thing I want: 12 months of sales history, by month, broken down by item. 

Since I was rebuilding it anyway, I added some calculations: 12 month average, 3 month average, trend (3m/12m), coefficient of variation (standard deviation/12m avg), and 12m peak (highest month out of the last 12). 

The BC report took 8 minutes, last I timed it. This one takes 9 seconds. 

## Stack
- Python
- SQLite
- Dynamics 365 Business Central OData API
- Azure Key Vault

## Usage
Requires internal Business Central credentials and Azure Key Vault authentication — not runnable externally. 

## Roadmap

- [x] Replace the built-in Sales History report with something better.

- [ ] Wire up Task Scheduler to automatically refresh the mirror every 15 minutes. 

- [ ] Set up a scheduled job to run every morning and email an alert about anything left in the ASSEMBLEOUT bin for more than 2 days. 
- [ ] Same thing for the SHIP bin. 

- [ ] Build clean silver-level tables off the raw bronze tables
