-- mart_daily_metrics: the canonical table. Every future source (GA4 Data API, Shopify,
-- ad platforms) feeds this same shape, so the intelligence layer never changes.
-- NOTE: users/new_users are distinct counts and are NOT additive across rows.
CREATE OR REPLACE TABLE `{project}.{dataset}.mart_daily_metrics` AS
SELECT
  session_date AS date,
  source, medium, campaign, device, country,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(DISTINCT IF(session_number = 1, user_pseudo_id, NULL)) AS new_users,
  COUNT(*) AS sessions,
  SUM(engaged) AS engaged_sessions,
  COUNTIF(viewed_item) AS sessions_with_product_view,
  COUNTIF(added_to_cart) AS sessions_with_add_to_cart,
  COUNTIF(began_checkout) AS sessions_with_checkout,
  COUNTIF(purchased) AS converting_sessions,
  SUM(transactions) AS transactions,
  ROUND(SUM(revenue), 2) AS revenue
FROM `{project}.{dataset}.stg_sessions`
GROUP BY 1, 2, 3, 4, 5, 6;
