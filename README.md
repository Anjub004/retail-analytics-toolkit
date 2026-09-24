# 🛒 Retail Analytics Toolkit

A ready-to-run toolkit for three questions every retail business asks:

1. **Where are we losing stock?** (shrinkage analysis)
2. **Are visitors turning into buyers?** (footfall & conversion)
3. **What will expire before it sells?** (short-expiry risk)

It ships with a **fully synthetic dataset** of 8 branches, 60 products and 6 months of daily sales, so you can run everything in two commands, then swap in your own data.

![Shrinkage by category and reason](reports/charts/shrink_by_category_reason.png)

## ✨ What's inside

| Folder | What it does |
|---|---|
| `data/generate_data.py` | Builds a realistic fake retail dataset (CSV + SQLite) |
| `sql/shrinkage.sql` | Shrink % by branch, category, reason, month; top loss products |
| `sql/footfall.sql` | Conversion rate, average basket, weekday and weekly patterns |
| `sql/short_expiry.sql` | Stock at risk of expiring unsold, using recent sales velocity |
| `analysis/run_analysis.py` | Runs every query, saves CSVs and charts, writes a summary report |
| `reports/` | Sample output: [summary.md](reports/summary.md), CSVs and charts |

## 🚀 Quick start

```bash
git clone https://github.com/Anjub004/retail-analytics-toolkit.git
cd retail-analytics-toolkit
pip install -r requirements.txt

python data/generate_data.py      # creates data/retail.db
python analysis/run_analysis.py   # creates reports/
```

Then open `reports/summary.md` for the findings.

## 📊 Sample findings

From the synthetic data (your numbers will differ with real data):

- One branch runs at **2x the network shrink rate**, a clear candidate for a stock-control review.
- **Expiry** is the single biggest cause of loss, driven by Fruit & Veg, Dairy and Bakery.
- Personal Care losses are mostly **Unknown/Theft**, a very different problem that needs a different fix.
- Saturday is the busiest day and Tuesday the quietest, useful for rostering and promotions.
- The expiry model flags specific batches that won't sell in time, so teams can **mark down, transfer or promote** them before they become waste.

| Shrink by branch | Stock by days to expiry |
|---|---|
| ![](reports/charts/shrink_by_branch.png) | ![](reports/charts/expiry_buckets.png) |

## 🧠 How the key metrics work

**Shrink %** = value of stock adjustments (at cost) ÷ sales revenue × 100.

**Conversion %** = transactions ÷ visitors × 100.

**Projected unsold at expiry** = stock on hand − (average daily sales over the last 28 days × days until expiry). If this is positive, that stock will likely expire on the shelf, and `value_at_risk` shows what it costs.

## 🗂️ Data model

| Table | Key columns |
|---|---|
| `branches` | branch_id, branch_name, size |
| `products` | product_id, product_name, category, unit_price, unit_cost, shelf_life_days |
| `sales` | date, branch_id, product_id, qty_sold, revenue |
| `footfall` | date, branch_id, visitors, transactions |
| `stock_adjustments` | date, branch_id, product_id, reason, qty, cost_value |
| `inventory_batches` | batch_id, branch_id, product_id, qty_on_hand, received_date, expiry_date |

## 🔌 Using your own data

1. Export your data as CSVs with the columns above.
2. Load them into a SQLite database at `data/retail.db` (see `main()` in `generate_data.py` for how).
3. Run `python analysis/run_analysis.py`.

The SQL is plain and portable, so it also adapts easily to BigQuery, PostgreSQL or MySQL, and the CSV outputs plug straight into Looker Studio, Power BI or Google Sheets.

## 🛣️ Ideas for next steps

- A Jupyter notebook walkthrough
- A Looker Studio / Power BI dashboard template
- ABC analysis and slow-mover detection
- Google Sheets + Apps Script version

## 📝 License

MIT. All data in this repository is synthetic and does not represent any real business.
