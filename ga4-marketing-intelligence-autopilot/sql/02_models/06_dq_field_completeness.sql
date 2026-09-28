-- dq_field_completeness: how much of each business field is unusable.
-- Feeds the "Data quality notes" section of the weekly brief.
CREATE OR REPLACE TABLE `{project}.{dataset}.dq_field_completeness` AS
WITH checks AS (
  SELECT 'sessions' AS table_name, 'source' AS field, source AS value FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'sessions', 'medium', medium FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'sessions', 'campaign', campaign FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'sessions', 'country', country FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'sessions', 'device', device FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'sessions', 'landing_page', landing_page FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'sessions', 'session_level_source', IF(source_scope = 'session', 'ok', NULL)
            FROM `{project}.{dataset}.stg_sessions`
  UNION ALL SELECT 'products', 'item_name', item_name FROM `{project}.{dataset}.mart_product_daily`
  UNION ALL SELECT 'products', 'item_category', item_category FROM `{project}.{dataset}.mart_product_daily`
)
SELECT
  table_name,
  field,
  COUNT(*) AS rows_checked,
  COUNTIF(value IS NULL OR TRIM(value) IN ('', '<Other>', '(not set)', '(data deleted)')) AS unusable_rows,
  ROUND(100 * SAFE_DIVIDE(
    COUNTIF(value IS NULL OR TRIM(value) IN ('', '<Other>', '(not set)', '(data deleted)')),
    COUNT(*)), 1) AS unusable_pct
FROM checks
GROUP BY table_name, field
ORDER BY unusable_pct DESC;
