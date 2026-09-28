-- stg_sessions: one row per GA4 session.
-- Flattens nested event_params and rolls events up to the session.
-- Session source uses session-level params where present, else the user's first touch.
CREATE OR REPLACE TABLE `{project}.{dataset}.stg_sessions` AS
WITH events AS (
  SELECT
    PARSE_DATE('%Y%m%d', event_date) AS event_date,
    event_timestamp,
    event_name,
    user_pseudo_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_number') AS ga_session_number,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source') AS ep_source,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium') AS ep_medium,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'campaign') AS ep_campaign,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_location,
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'engagement_time_msec') AS engagement_time_msec,
    (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING))
       FROM UNNEST(event_params) WHERE key = 'session_engaged') AS session_engaged,
    traffic_source.source AS ft_source,
    traffic_source.medium AS ft_medium,
    traffic_source.name   AS ft_campaign,
    device.category AS device,
    geo.country AS country,
    ecommerce.purchase_revenue AS purchase_revenue
  FROM `{source}.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '{start}' AND '{end}'
)
SELECT
  CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING)) AS session_key,
  user_pseudo_id,
  MIN(event_date) AS session_date,
  TIMESTAMP_MICROS(MIN(event_timestamp)) AS session_start_ts,
  MIN(ga_session_number) AS session_number,
  COALESCE(ARRAY_AGG(ep_source IGNORE NULLS ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)], ANY_VALUE(ft_source)) AS source,
  COALESCE(ARRAY_AGG(ep_medium IGNORE NULLS ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)], ANY_VALUE(ft_medium)) AS medium,
  COALESCE(ARRAY_AGG(ep_campaign IGNORE NULLS ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)], ANY_VALUE(ft_campaign)) AS campaign,
  IF(COUNTIF(ep_source IS NOT NULL) > 0, 'session', 'first_touch') AS source_scope,
  ANY_VALUE(device) AS device,
  ANY_VALUE(country) AS country,
  ARRAY_AGG(IF(event_name = 'page_view', page_location, NULL) IGNORE NULLS ORDER BY event_timestamp LIMIT 1)[SAFE_OFFSET(0)] AS landing_page,
  COUNT(*) AS events,
  COUNTIF(event_name = 'page_view') AS pageviews,
  COUNTIF(event_name = 'view_item') > 0 AS viewed_item,
  COUNTIF(event_name = 'add_to_cart') > 0 AS added_to_cart,
  COUNTIF(event_name = 'begin_checkout') > 0 AS began_checkout,
  COUNTIF(event_name = 'purchase') > 0 AS purchased,
  COUNTIF(event_name = 'purchase') AS transactions,
  SUM(IF(event_name = 'purchase', IFNULL(purchase_revenue, 0), 0)) AS revenue,
  MAX(IF(session_engaged = '1', 1, 0)) AS engaged,
  SUM(IFNULL(engagement_time_msec, 0)) / 1000 AS engagement_seconds
FROM events
WHERE ga_session_id IS NOT NULL
GROUP BY session_key, user_pseudo_id;
