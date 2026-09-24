-- Footfall & conversion analysis
-- Conversion = transactions / visitors. Basket value = revenue / transactions.

-- name: branch_conversion
WITH rev AS (
    SELECT branch_id, SUM(revenue) AS revenue FROM sales GROUP BY branch_id
)
SELECT b.branch_id,
       b.branch_name,
       SUM(f.visitors)                                         AS visitors,
       SUM(f.transactions)                                     AS transactions,
       ROUND(100.0 * SUM(f.transactions) / SUM(f.visitors), 1) AS conversion_pct,
       ROUND(rev.revenue / SUM(f.transactions), 2)             AS avg_basket
FROM footfall f
JOIN branches b ON b.branch_id = f.branch_id
JOIN rev ON rev.branch_id = f.branch_id
GROUP BY b.branch_id
ORDER BY visitors DESC;

-- name: weekday_pattern
SELECT CASE strftime('%w', date)
           WHEN '1' THEN '1-Mon' WHEN '2' THEN '2-Tue' WHEN '3' THEN '3-Wed'
           WHEN '4' THEN '4-Thu' WHEN '5' THEN '5-Fri' WHEN '6' THEN '6-Sat'
           ELSE '7-Sun' END                                  AS weekday,
       ROUND(AVG(visitors), 0)                               AS avg_visitors,
       ROUND(100.0 * SUM(transactions) / SUM(visitors), 1)   AS conversion_pct
FROM footfall
GROUP BY weekday
ORDER BY weekday;

-- name: weekly_trend
SELECT strftime('%Y-W%W', date) AS week,
       SUM(visitors)            AS visitors,
       SUM(transactions)        AS transactions
FROM footfall
GROUP BY week
ORDER BY week;
