-- dim_users: one row per user. Foundation for new/returning, RFM and CLV (Tuesday).
CREATE OR REPLACE TABLE `{project}.{dataset}.dim_users` AS
SELECT
  user_pseudo_id,
  MIN(session_date) AS first_seen,
  MAX(session_date) AS last_seen,
  COUNT(*) AS sessions,
  SUM(transactions) AS purchases,
  ROUND(SUM(revenue), 2) AS revenue,
  MIN(IF(transactions > 0, session_date, NULL)) AS first_purchase_date,
  MAX(IF(transactions > 0, session_date, NULL)) AS last_purchase_date,
  ARRAY_AGG(source IGNORE NULLS ORDER BY session_start_ts LIMIT 1)[SAFE_OFFSET(0)] AS first_source,
  ARRAY_AGG(medium IGNORE NULLS ORDER BY session_start_ts LIMIT 1)[SAFE_OFFSET(0)] AS first_medium,
  ARRAY_AGG(device IGNORE NULLS ORDER BY session_start_ts LIMIT 1)[SAFE_OFFSET(0)] AS first_device,
  ANY_VALUE(country) AS country,
  MIN(session_number) = 1 AS new_in_window
FROM `{project}.{dataset}.stg_sessions`
GROUP BY user_pseudo_id;
