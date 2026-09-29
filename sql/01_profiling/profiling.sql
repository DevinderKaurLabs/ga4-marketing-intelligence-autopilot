-- Run these one at a time in the BigQuery console to get a feel for the data.
-- Each scans only a few columns, well inside the 1 TB/month free tier.

-- 1. Scale and date range
SELECT MIN(event_date) AS first_day, MAX(event_date) AS last_day,
       COUNT(*) AS events, COUNT(DISTINCT user_pseudo_id) AS users
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`;

-- 2. Which events exist (the raw material of the funnel)
SELECT event_name, COUNT(*) AS events
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1 ORDER BY 2 DESC;

-- 3. Which parameters live inside event_params (nested, needs UNNEST)
SELECT ep.key, COUNT(*) AS occurrences
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`, UNNEST(event_params) AS ep
GROUP BY 1 ORDER BY 2 DESC;

-- 4. Daily revenue: look for Black Friday (27 Nov 2020) and the post-Christmas drop
SELECT PARSE_DATE('%Y%m%d', event_date) AS day,
       COUNTIF(event_name = 'purchase') AS purchases,
       ROUND(SUM(IF(event_name = 'purchase', IFNULL(ecommerce.purchase_revenue, 0), 0)), 2) AS revenue
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1 ORDER BY 1;

-- 5. First-touch acquisition mix (note how much is <Other> or (data deleted))
SELECT traffic_source.source, traffic_source.medium, COUNT(DISTINCT user_pseudo_id) AS users
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 20;

-- 6. Device and country split
SELECT device.category, geo.country, COUNT(DISTINCT user_pseudo_id) AS users
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 20;
