# Demand Analytics

Demand analysis tools for a local SQLite mirror of Dynamics 365 Business Central

## About

Got tired of clicking around the Business Central frontend UI, waiting endlessly for tables to download to Excel, and then manually joining them over and over. So I taught myself Python and SQL. 

### mirror.py

This is the core of everything. Business Central doesn't expose the ERP data for direct SQL querying, so this hits the Odata endpoints and downloads to a local SQLite file. There's a `watermark` table that logs the latest record seen on each table, and only pulls the new ones. This keeps each refresh light and fast. 

### sales_history.py

BC's built in Sales History report takes a starting date and a period length and returns 8 periods — 8 months, 8 days, 8 years, however you like. Why 8? No idea. All I know is it takes forever to run and doesn't even give me what I need to do my job: 12 months of sales history, by month, broken down by item. 

Once I had `mirror.py` built, the `Posted Sales Invoice Lines` were just sitting there, ready to be queried and aggregated. Then, since I was rebuilding it anyway, I added some calculations: 12 month average, 3 month average, trend (3m/12m), coefficient of variation (standard deviation/12m avg), and 12m peak (highest month out of the last 12). 

Runs in seconds and automatically opens the file in Excel. Pretty slick. 

## Stack
- Python
- SQLite
- Dynamics 365 Business Central OData API
- Azure Key Vault
- Dependencies listed in requirements.txt

## Usage
Configured for a specific internal environment with our existing Azure Key Vault setup, but should work with any method of authenticating a Python query against a BC OData API endpoint. 

## Roadmap

- [x] Replace the built-in Sales History report with something better.
- [x] Wire up Task Scheduler to automatically refresh the mirror every 15 minutes. 
- [x] Set up a scheduled job to run every morning and email an alert about anything left in the ASSEMBLEOUT bin for more than 2 days. 
- [ ] Same thing for the SHIP bin. 
- [ ] Build clean silver-level tables off the raw bronze tables
