"""
Generate a realistic, fully synthetic retail dataset.

Creates CSV files in data/raw/ and a SQLite database at data/retail.db with:
  branches, products, sales, footfall, stock_adjustments, inventory_batches

All names and numbers are fake. Run:
    python data/generate_data.py
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DAYS = 180
END_DATE = date(2026, 6, 30)
START_DATE = END_DATE - timedelta(days=DAYS - 1)

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
DB_PATH = ROOT / "retail.db"

rng = np.random.default_rng(SEED)

BRANCHES = [
    ("B01", "Northgate", "Large", 1.40),
    ("B02", "Riverside", "Large", 1.25),
    ("B03", "Hillview", "Medium", 1.00),
    ("B04", "Lakeside", "Medium", 0.95),
    ("B05", "Old Town", "Medium", 0.90),
    ("B06", "Sunset Park", "Small", 0.65),
    ("B07", "Greenfield", "Small", 0.60),
    ("B08", "Airport Road", "Small", 0.55),
]

# category: (item count, price range, margin, shelf life range in days, shrink tendency)
CATEGORIES = {
    "Dairy": (8, (1.5, 6.0), 0.22, (7, 21), 1.6),
    "Bakery": (7, (1.0, 5.0), 0.35, (2, 5), 2.2),
    "Fruit & Veg": (10, (0.8, 4.0), 0.30, (4, 12), 2.5),
    "Beverages": (8, (0.9, 8.0), 0.25, (180, 365), 0.6),
    "Grocery": (10, (1.2, 12.0), 0.20, (180, 720), 0.5),
    "Frozen": (6, (2.5, 10.0), 0.24, (90, 270), 0.8),
    "Household": (6, (2.0, 15.0), 0.28, (365, 1095), 0.7),
    "Personal Care": (5, (2.5, 18.0), 0.32, (365, 1095), 1.3),
}

REASONS = ["Damage", "Expiry", "Unknown/Theft", "Admin Error"]


def build_branches() -> pd.DataFrame:
    return pd.DataFrame(BRANCHES, columns=["branch_id", "branch_name", "size", "traffic_factor"])


def build_products() -> pd.DataFrame:
    rows = []
    pid = 1
    for cat, (count, (pmin, pmax), margin, (smin, smax), shrink) in CATEGORIES.items():
        for i in range(count):
            price = round(float(rng.uniform(pmin, pmax)), 2)
            rows.append({
                "product_id": f"P{pid:03d}",
                "product_name": f"{cat} Item {i + 1:02d}",
                "category": cat,
                "unit_price": price,
                "unit_cost": round(price * (1 - margin), 2),
                "shelf_life_days": int(rng.integers(smin, smax + 1)),
                "shrink_tendency": shrink,
                "base_daily_units": round(float(rng.uniform(3, 25)), 1),
            })
            pid += 1
    return pd.DataFrame(rows)


def build_footfall(branches: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    weekday_factor = {0: 0.85, 1: 0.80, 2: 0.85, 3: 0.95, 4: 1.20, 5: 1.35, 6: 1.10}
    rows = []
    for _, b in branches.iterrows():
        base = 1800 * b.traffic_factor
        for d in dates:
            payday_boost = 1.15 if d.day >= 25 or d.day <= 2 else 1.0
            visitors = base * weekday_factor[d.weekday()] * payday_boost * rng.normal(1, 0.08)
            conversion = np.clip(rng.normal(0.62, 0.05), 0.4, 0.85)
            rows.append({
                "date": d.date().isoformat(),
                "branch_id": b.branch_id,
                "visitors": int(visitors),
                "transactions": int(visitors * conversion),
            })
    return pd.DataFrame(rows)


def build_sales(branches, products, footfall) -> pd.DataFrame:
    traffic = footfall.set_index(["branch_id", "date"])["transactions"]
    avg_tx = footfall.groupby("branch_id")["transactions"].mean()
    rows = []
    for _, b in branches.iterrows():
        for _, p in products.iterrows():
            branch_pref = rng.uniform(0.7, 1.3)
            for d in pd.date_range(START_DATE, END_DATE, freq="D"):
                ds = d.date().isoformat()
                demand = (
                    p.base_daily_units * b.traffic_factor * branch_pref
                    * traffic[(b.branch_id, ds)] / avg_tx[b.branch_id]
                )
                qty = int(rng.poisson(max(demand, 0.1)))
                if qty == 0:
                    continue
                rows.append({
                    "date": ds,
                    "branch_id": b.branch_id,
                    "product_id": p.product_id,
                    "qty_sold": qty,
                    "revenue": round(qty * p.unit_price, 2),
                })
    return pd.DataFrame(rows)


def build_adjustments(branches, products) -> pd.DataFrame:
    # Some branches are deliberately "leakier" so the analysis has something to find.
    branch_leak = {"B01": 1.0, "B02": 0.9, "B03": 1.1, "B04": 0.8,
                   "B05": 1.8, "B06": 1.0, "B07": 1.4, "B08": 0.9}
    rows = []
    adj_id = 1
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    for _, b in branches.iterrows():
        for _, p in products.iterrows():
            rate = 0.035 * p.shrink_tendency * branch_leak[b.branch_id]
            for d in dates:
                if rng.random() > rate:
                    continue
                if p.shelf_life_days <= 21:
                    probs = [0.20, 0.55, 0.15, 0.10]
                elif p.category == "Personal Care":
                    probs = [0.15, 0.05, 0.65, 0.15]
                else:
                    probs = [0.40, 0.15, 0.25, 0.20]
                reason = rng.choice(REASONS, p=probs)
                qty = int(rng.integers(1, 8))
                rows.append({
                    "adjustment_id": f"A{adj_id:06d}",
                    "date": d.date().isoformat(),
                    "branch_id": b.branch_id,
                    "product_id": p.product_id,
                    "reason": reason,
                    "qty": qty,
                    "cost_value": round(qty * p.unit_cost, 2),
                })
                adj_id += 1
    return pd.DataFrame(rows)


def build_batches(branches, products) -> pd.DataFrame:
    """Current stock on hand (as of END_DATE), split into batches with expiry dates."""
    rows = []
    batch_id = 1
    for _, b in branches.iterrows():
        for _, p in products.iterrows():
            for _ in range(int(rng.integers(1, 4))):
                received_ago = int(rng.integers(0, max(2, min(p.shelf_life_days, 60))))
                received = END_DATE - timedelta(days=received_ago)
                expiry = received + timedelta(days=int(p.shelf_life_days))
                if expiry < END_DATE:
                    continue
                rows.append({
                    "batch_id": f"BT{batch_id:06d}",
                    "branch_id": b.branch_id,
                    "product_id": p.product_id,
                    "qty_on_hand": int(p.base_daily_units * b.traffic_factor * rng.uniform(0.5, 4)),
                    "received_date": received.isoformat(),
                    "expiry_date": expiry.isoformat(),
                })
                batch_id += 1
    return pd.DataFrame(rows)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating data for {START_DATE} to {END_DATE} ...")

    branches = build_branches()
    products = build_products()
    footfall = build_footfall(branches)
    sales = build_sales(branches, products, footfall)
    adjustments = build_adjustments(branches, products)
    batches = build_batches(branches, products)

    tables = {
        "branches": branches.drop(columns=["traffic_factor"]),
        "products": products.drop(columns=["shrink_tendency", "base_daily_units"]),
        "footfall": footfall,
        "sales": sales,
        "stock_adjustments": adjustments,
        "inventory_batches": batches,
    }

    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as conn:
        for name, df in tables.items():
            df.to_csv(RAW_DIR / f"{name}.csv", index=False)
            df.to_sql(name, conn, index=False)
            print(f"  {name:<18} {len(df):>7,} rows")
        conn.executescript("""
            CREATE INDEX idx_sales_bpd ON sales(branch_id, product_id, date);
            CREATE INDEX idx_adj_bpd ON stock_adjustments(branch_id, product_id, date);
        """)

    print(f"Done. Database: {DB_PATH.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
