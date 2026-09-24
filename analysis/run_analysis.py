"""
Run every query in sql/, save results to reports/, draw charts, and write
a short Markdown summary with the key findings.

    python analysis/run_analysis.py
"""

import re
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "retail.db"
SQL_DIR = ROOT / "sql"
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"

plt.rcParams.update({
    "figure.figsize": (9, 5),
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
})


def load_queries(path: Path) -> dict[str, str]:
    """Split a .sql file into named queries using '-- name: <query_name>' markers."""
    text = path.read_text()
    parts = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run_all(conn) -> dict[str, pd.DataFrame]:
    results = {}
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        for name, query in load_queries(sql_file).items():
            df = pd.read_sql_query(query, conn)
            df.to_csv(REPORTS / f"{name}.csv", index=False)
            results[name] = df
            print(f"  {sql_file.name:<18} {name:<28} {len(df):>5} rows")
    return results


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHARTS / f"{name}.png", dpi=130)
    plt.close(fig)


def draw_charts(r: dict[str, pd.DataFrame]) -> None:
    # 1. Shrink % by branch
    df = r["shrink_by_branch"].sort_values("shrink_pct")
    fig, ax = plt.subplots()
    avg = df["shrink_value"].sum() / df["revenue"].sum() * 100
    colors = ["#d9534f" if v > avg else "#5b8def" for v in df["shrink_pct"]]
    ax.barh(df["branch_name"], df["shrink_pct"], color=colors)
    ax.axvline(avg, ls="--", color="grey", label=f"Network avg {avg:.2f}%")
    ax.set(title="Shrinkage % of Sales by Branch", xlabel="Shrink % of revenue")
    ax.legend()
    save(fig, "shrink_by_branch")

    # 2. Shrink value by category and reason (stacked)
    pivot = r["shrink_by_category_reason"].pivot_table(
        index="category", columns="reason", values="shrink_value", aggfunc="sum"
    ).fillna(0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values().index]
    fig, ax = plt.subplots()
    pivot.plot(kind="barh", stacked=True, ax=ax, colormap="tab20c")
    ax.set(title="Where Is the Loss Coming From?", xlabel="Shrink value (cost)", ylabel="")
    save(fig, "shrink_by_category_reason")

    # 3. Weekday footfall pattern
    df = r["weekday_pattern"]
    fig, ax = plt.subplots()
    ax.bar(df["weekday"].str[2:], df["avg_visitors"], color="#5b8def")
    ax.set(title="Average Daily Visitors by Weekday", ylabel="Visitors per branch")
    save(fig, "weekday_pattern")

    # 4. Weekly footfall trend
    df = r["weekly_trend"]
    fig, ax = plt.subplots()
    ax.plot(df["week"], df["visitors"], marker="o", ms=3, label="Visitors")
    ax.plot(df["week"], df["transactions"], marker="o", ms=3, label="Transactions")
    ax.set(title="Weekly Footfall vs Transactions (all branches)")
    ax.set_xticks(df["week"][::3])
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    save(fig, "weekly_trend")

    # 5. Stock value by days-to-expiry bucket
    df = r["expiry_buckets"]
    fig, ax = plt.subplots()
    ax.bar(df["bucket"], df["stock_value"], color=["#d9534f", "#f0ad4e", "#f7d774", "#5cb85c"][: len(df)])
    ax.set(title="Stock Value by Days to Expiry", ylabel="Stock value (cost)")
    save(fig, "expiry_buckets")


def write_summary(r: dict[str, pd.DataFrame]) -> None:
    sb = r["shrink_by_branch"]
    net_pct = sb["shrink_value"].sum() / sb["revenue"].sum() * 100
    worst = sb.iloc[0]
    cat = r["shrink_by_category_reason"].groupby("category")["shrink_value"].sum().idxmax()
    reason = r["shrink_by_category_reason"].groupby("reason")["shrink_value"].sum()
    conv = r["branch_conversion"]
    best_conv = conv.loc[conv["conversion_pct"].idxmax()]
    wk = r["weekday_pattern"]
    busiest = wk.loc[wk["avg_visitors"].idxmax(), "weekday"][2:]
    quietest = wk.loc[wk["avg_visitors"].idxmin(), "weekday"][2:]
    risk = r["expiry_risk"]

    lines = [
        "# Retail Analytics Summary",
        "",
        "_Generated from synthetic data by `analysis/run_analysis.py`._",
        "",
        "## Shrinkage",
        f"- Network shrink is **{net_pct:.2f}%** of sales.",
        f"- Highest-shrink branch: **{worst.branch_name}** at **{worst.shrink_pct:.2f}%** "
        f"({worst.shrink_pct / net_pct:.1f}x the network average).",
        f"- Category losing the most value: **{cat}**.",
        f"- Biggest loss reason overall: **{reason.idxmax()}** "
        f"({reason.max() / reason.sum() * 100:.0f}% of shrink value).",
        "",
        "![Shrink by branch](charts/shrink_by_branch.png)",
        "![Shrink by category](charts/shrink_by_category_reason.png)",
        "",
        "## Footfall & Conversion",
        f"- Busiest day: **{busiest}**; quietest day: **{quietest}**.",
        f"- Best conversion: **{best_conv.branch_name}** at **{best_conv.conversion_pct}%**.",
        "",
        "![Weekday pattern](charts/weekday_pattern.png)",
        "![Weekly trend](charts/weekly_trend.png)",
        "",
        "## Short-Expiry Risk (next 30 days)",
        f"- **{len(risk)}** batches are projected to have unsold stock at expiry.",
        f"- Estimated value at risk: **{risk['value_at_risk'].sum():,.2f}** (at cost).",
        "",
        "Top 5 batches to act on (markdown, transfer or promote):",
        "",
        risk.head(5)[["branch_name", "product_name", "days_left", "qty_on_hand",
                      "projected_unsold", "value_at_risk"]].to_markdown(index=False),
        "",
        "![Expiry buckets](charts/expiry_buckets.png)",
        "",
    ]
    (REPORTS / "summary.md").write_text("\n".join(lines))


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run `python data/generate_data.py` first.")
    CHARTS.mkdir(parents=True, exist_ok=True)

    print("Running queries ...")
    with sqlite3.connect(DB_PATH) as conn:
        results = run_all(conn)

    print("Drawing charts ...")
    draw_charts(results)
    write_summary(results)
    print(f"Done. Open {(REPORTS / 'summary.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
