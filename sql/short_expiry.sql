-- Short-expiry risk analysis
-- Compares stock on hand with recent sales velocity to estimate
-- how much stock will NOT sell before it expires.
-- Snapshot date = last date in the sales table.

-- name: expiry_risk
WITH snap AS (
    SELECT MAX(date) AS d FROM sales
),
velocity AS (
    SELECT s.branch_id, s.product_id, SUM(s.qty_sold) / 28.0 AS avg_daily_units
    FROM sales s, snap
    WHERE s.date > date(snap.d, '-28 days')
    GROUP BY s.branch_id, s.product_id
),
batches AS (
    SELECT i.*,
           CAST(julianday(i.expiry_date) - julianday(snap.d) AS INTEGER) AS days_left
    FROM inventory_batches i, snap
)
SELECT b.branch_id,
       br.branch_name,
       p.product_name,
       p.category,
       b.batch_id,
       b.qty_on_hand,
       b.expiry_date,
       b.days_left,
       ROUND(COALESCE(v.avg_daily_units, 0), 1) AS avg_daily_units,
       CAST(b.qty_on_hand - COALESCE(v.avg_daily_units, 0) * b.days_left AS INTEGER)
                                                AS projected_unsold,
       ROUND((b.qty_on_hand - COALESCE(v.avg_daily_units, 0) * b.days_left)
             * p.unit_cost, 2)                  AS value_at_risk
FROM batches b
JOIN products p  ON p.product_id = b.product_id
JOIN branches br ON br.branch_id = b.branch_id
LEFT JOIN velocity v ON v.branch_id = b.branch_id AND v.product_id = b.product_id
WHERE b.days_left <= 30
  AND b.qty_on_hand - COALESCE(v.avg_daily_units, 0) * b.days_left >= 1
ORDER BY value_at_risk DESC;

-- name: expiry_buckets
WITH snap AS (SELECT MAX(date) AS d FROM sales)
SELECT CASE
           WHEN julianday(i.expiry_date) - julianday(snap.d) <= 7  THEN '0-7 days'
           WHEN julianday(i.expiry_date) - julianday(snap.d) <= 14 THEN '8-14 days'
           WHEN julianday(i.expiry_date) - julianday(snap.d) <= 30 THEN '15-30 days'
           ELSE '30+ days' END                     AS bucket,
       COUNT(*)                                    AS batches,
       SUM(i.qty_on_hand)                          AS units,
       ROUND(SUM(i.qty_on_hand * p.unit_cost), 2)  AS stock_value
FROM inventory_batches i
JOIN products p ON p.product_id = i.product_id
CROSS JOIN snap
GROUP BY bucket
ORDER BY MIN(julianday(i.expiry_date));
