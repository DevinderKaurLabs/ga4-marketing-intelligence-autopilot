-- mart_product_daily: product funnel per day (views -> adds -> purchases -> revenue).
CREATE OR REPLACE TABLE `{project}.{dataset}.mart_product_daily` AS
SELECT
  PARSE_DATE('%Y%m%d', e.event_date) AS date,
  i.item_id,
  i.item_name,
  i.item_category,
  COUNTIF(e.event_name = 'view_item') AS views,
  COUNTIF(e.event_name = 'add_to_cart') AS adds_to_cart,
  COUNTIF(e.event_name = 'purchase') AS purchase_lines,
  SUM(IF(e.event_name = 'purchase', IFNULL(i.quantity, 0), 0)) AS units,
  ROUND(SUM(IF(e.event_name = 'purchase',
               COALESCE(i.item_revenue, i.price * i.quantity, 0), 0)), 2) AS item_revenue
FROM `{source}.events_*` AS e, UNNEST(e.items) AS i
WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
  AND e.event_name IN ('view_item', 'add_to_cart', 'purchase')
GROUP BY 1, 2, 3, 4;
