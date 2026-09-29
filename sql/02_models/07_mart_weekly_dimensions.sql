-- mart_weekly_dimensions: one row per week (Mon-Sun) x dimension x value.
-- Distinct users are counted here in BigQuery so weekly numbers stay correct.
-- Dimensions: total, channel (source / medium), device, country, campaign.
CREATE OR REPLACE TABLE `{project}.{dataset}.mart_weekly_dimensions` AS
WITH s AS (
  SELECT
    DATE_TRUNC(session_date, WEEK(MONDAY)) AS week_start,
    session_date, user_pseudo_id, session_number, engaged,
    viewed_item, added_to_cart, began_checkout, purchased, transactions, revenue,
    CONCAT(IFNULL(source, '(none)'), ' / ', IFNULL(medium, '(none)')) AS channel,
    IFNULL(device, '(not set)') AS device,
    IFNULL(country, '(not set)') AS country,
    IFNULL(campaign, '(not set)') AS campaign
  FROM `{project}.{dataset}.stg_sessions`
),
long AS (
  SELECT week_start, session_date, 'total' AS dimension, 'All traffic' AS dimension_value,
         user_pseudo_id, session_number, engaged, viewed_item, added_to_cart,
         began_checkout, purchased, transactions, revenue FROM s
  UNION ALL
  SELECT week_start, session_date, 'channel', channel, user_pseudo_id, session_number, engaged,
         viewed_item, added_to_cart, began_checkout, purchased, transactions, revenue FROM s
  UNION ALL
  SELECT week_start, session_date, 'device', device, user_pseudo_id, session_number, engaged,
         viewed_item, added_to_cart, began_checkout, purchased, transactions, revenue FROM s
  UNION ALL
  SELECT week_start, session_date, 'country', country, user_pseudo_id, session_number, engaged,
         viewed_item, added_to_cart, began_checkout, purchased, transactions, revenue FROM s
  UNION ALL
  SELECT week_start, session_date, 'campaign', campaign, user_pseudo_id, session_number, engaged,
         viewed_item, added_to_cart, began_checkout, purchased, transactions, revenue FROM s
)
SELECT
  week_start,
  dimension,
  dimension_value,
  COUNT(DISTINCT session_date) AS days_in_data,
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
FROM long
GROUP BY week_start, dimension, dimension_value;
