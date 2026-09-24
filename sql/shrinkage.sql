-- Shrinkage analysis
-- Shrink % = value lost through stock adjustments / sales revenue.

-- name: shrink_by_branch
WITH s AS (
    SELECT branch_id, SUM(revenue) AS revenue FROM sales GROUP BY branch_id
),
a AS (
    SELECT branch_id, SUM(cost_value) AS shrink_value FROM stock_adjustments GROUP BY branch_id
)
SELECT b.branch_id,
       b.branch_name,
       ROUND(s.revenue, 2)                          AS revenue,
       ROUND(a.shrink_value, 2)                     AS shrink_value,
       ROUND(100.0 * a.shrink_value / s.revenue, 2) AS shrink_pct
FROM branches b
JOIN s ON s.branch_id = b.branch_id
JOIN a ON a.branch_id = b.branch_id
ORDER BY shrink_pct DESC;

-- name: shrink_by_category_reason
SELECT p.category,
       a.reason,
       SUM(a.qty)                  AS units_lost,
       ROUND(SUM(a.cost_value), 2) AS shrink_value
FROM stock_adjustments a
JOIN products p ON p.product_id = a.product_id
GROUP BY p.category, a.reason
ORDER BY p.category, shrink_value DESC;

-- name: shrink_monthly_trend
WITH s AS (
    SELECT substr(date, 1, 7) AS month, SUM(revenue) AS revenue FROM sales GROUP BY month
),
a AS (
    SELECT substr(date, 1, 7) AS month, SUM(cost_value) AS shrink_value
    FROM stock_adjustments GROUP BY month
)
SELECT s.month,
       ROUND(s.revenue, 2)                          AS revenue,
       ROUND(a.shrink_value, 2)                     AS shrink_value,
       ROUND(100.0 * a.shrink_value / s.revenue, 2) AS shrink_pct
FROM s JOIN a ON a.month = s.month
ORDER BY s.month;

-- name: top_shrink_products
SELECT p.product_id,
       p.product_name,
       p.category,
       SUM(a.qty)                  AS units_lost,
       ROUND(SUM(a.cost_value), 2) AS shrink_value
FROM stock_adjustments a
JOIN products p ON p.product_id = a.product_id
GROUP BY p.product_id
ORDER BY shrink_value DESC
LIMIT 10;
