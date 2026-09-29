-- fct_transactions: one row per purchase event.
CREATE OR REPLACE TABLE `{project}.{dataset}.fct_transactions` AS
SELECT
  PARSE_DATE('%Y%m%d', event_date) AS transaction_date,
  TIMESTAMP_MICROS(event_timestamp) AS transaction_ts,
  user_pseudo_id,
  CONCAT(user_pseudo_id, '-', CAST(
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_key,
  ecommerce.transaction_id,
  IFNULL(ecommerce.purchase_revenue, 0) AS revenue,
  ecommerce.total_item_quantity AS items,
  device.category AS device,
  geo.country AS country
FROM `{source}.events_*`
WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
  AND event_name = 'purchase';
