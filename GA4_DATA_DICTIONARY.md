# GA4 Data Dictionary

Source: `bigquery-public-data.ga4_obfuscated_sample_ecommerce` (Google Merchandise Store, public obfuscated GA4 export sample).
Generated automatically by `scripts/build_data_dictionary.py` on 2026-09-28.

> Architecture demonstration on Google's public 2020-21 sample. Obfuscated values
> (`<Other>`, NULL, '') are expected. The same code runs on any GA4 BigQuery export
> by changing `GA4_SOURCE`.

## Overview

| Metric | Value |
|---|---|
| Date range | 20201101 to 20210131 |
| Events | 4,295,584 |
| Users (user_pseudo_id) | 270,154 |
| Purchase events | 5,692 |
| Purchase revenue | 362,165.00 |

## Event inventory

| event_name | Events | Users |
|---|---|---|
| `page_view` | 1,350,428 | 269,792 |
| `user_engagement` | 1,058,721 | 213,004 |
| `scroll` | 493,072 | 138,098 |
| `view_item` | 386,068 | 61,252 |
| `session_start` | 354,970 | 267,116 |
| `first_visit` | 257,462 | 257,314 |
| `view_promotion` | 190,104 | 102,443 |
| `add_to_cart` | 58,543 | 12,545 |
| `begin_checkout` | 38,757 | 9,715 |
| `select_item` | 31,007 | 13,180 |
| `view_search_results` | 26,172 | 14,449 |
| `add_shipping_info` | 19,722 | 9,714 |
| `add_payment_info` | 13,899 | 5,751 |
| `select_promotion` | 9,450 | 8,164 |
| `purchase` | 5,692 | 4,419 |
| `click` | 1,446 | 1,010 |
| `view_item_list` | 71 | 44 |

## Event parameter inventory

`event_params` is a repeated record, so every parameter is read with `UNNEST`.

| Key | Occurrences | Stored in | Seen on events |
|---|---|---|---|
| `page_location` | 4,295,584 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `ga_session_id` | 4,295,584 | value.int_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `ga_session_number` | 4,295,584 | value.int_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `page_title` | 4,276,104 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `engaged_session_event` | 4,116,237 | value.int_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `session_engaged` | 3,996,312 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `debug_mode` | 3,682,991 | value.int_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `page_referrer` | 3,206,512 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, first_visit |
| `all_data` | 2,828,174 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `clean_event` | 2,828,040 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `engagement_time_msec` | 2,431,818 | value.int_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `medium` | 1,439,214 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `campaign` | 1,439,167 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `source` | 1,428,080 | value.string_value | add_payment_info, add_shipping_info, add_to_cart, begin_checkout, click, page_view |
| `percent_scrolled` | 493,072 | value.int_value | scroll |
| `term` | 338,704 | value.string_value | add_to_cart, begin_checkout, click, page_view, scroll, select_item |
| `entrances` | 332,179 | value.int_value | page_view |
| `gclid` | 118,481 | value.string_value | add_to_cart, click, page_view, scroll, select_item, select_promotion |
| `gclsrc` | 116,846 | value.string_value | add_to_cart, click, page_view, scroll, select_item, select_promotion |
| `currency` | 39,313 | value.string_value | add_payment_info, add_shipping_info, purchase |
| `search_term` | 26,172 | value.string_value | view_search_results |
| `unique_search_term` | 20,967 | value.int_value | view_search_results |
| `dclid` | 15,701 | value.string_value | add_to_cart, page_view, scroll, select_item, user_engagement, view_item |
| `transaction_id` | 5,242 | value.string_value | purchase |
| `tax` | 5,242 | value.double_value | purchase |
| `value` | 5,242 | value.double_value | purchase |
| `payment_type` | 5,242 | value.string_value | purchase |
| `shipping_tier` | 4,159 | value.string_value | purchase |
| `coupon` | 3,075 | value.string_value | purchase |
| `promotion_name` | 2,270 | value.string_value | purchase |
| `outbound` | 1,446 | value.string_value | click |
| `link_url` | 1,446 | value.string_value | click |
| `link_domain` | 1,446 | value.string_value | click |
| `link_classes` | 6 | value.string_value | click |

## Schema

| Field | Type | Business meaning | Used for |
|---|---|---|---|
| `event_date` | STRING | Date of the event (YYYYMMDD, property time zone) | All time series |
| `event_timestamp` | INTEGER | Event time in microseconds (UTC) | Session ordering |
| `event_name` | STRING | Action performed: page_view, add_to_cart, purchase... | Funnel, KPIs |
| `event_params` | REPEATED RECORD | Repeated key/value context for the event | Sessions, pages, session source |
| `event_params.key` | STRING |  |  |
| `event_params.value` | RECORD |  |  |
| `event_params.value.string_value` | STRING |  |  |
| `event_params.value.int_value` | INTEGER |  |  |
| `event_params.value.float_value` | FLOAT |  |  |
| `event_params.value.double_value` | FLOAT |  |  |
| `event_previous_timestamp` | INTEGER |  |  |
| `event_value_in_usd` | FLOAT |  |  |
| `event_bundle_sequence_id` | INTEGER |  |  |
| `event_server_timestamp_offset` | INTEGER |  |  |
| `user_id` | STRING |  |  |
| `user_pseudo_id` | STRING | Pseudonymous browser/device ID | Users, customers, RFM |
| `privacy_info` | RECORD |  |  |
| `privacy_info.analytics_storage` | INTEGER |  |  |
| `privacy_info.ads_storage` | INTEGER |  |  |
| `privacy_info.uses_transient_token` | STRING |  |  |
| `user_properties` | REPEATED RECORD |  |  |
| `user_properties.key` | INTEGER |  |  |
| `user_properties.value` | RECORD |  |  |
| `user_properties.value.string_value` | INTEGER |  |  |
| `user_properties.value.int_value` | INTEGER |  |  |
| `user_properties.value.float_value` | INTEGER |  |  |
| `user_properties.value.double_value` | INTEGER |  |  |
| `user_properties.value.set_timestamp_micros` | INTEGER |  |  |
| `user_first_touch_timestamp` | INTEGER | First time the user was seen | New vs returning |
| `user_ltv` | RECORD |  |  |
| `user_ltv.revenue` | FLOAT |  |  |
| `user_ltv.currency` | STRING |  |  |
| `device` | RECORD |  |  |
| `device.category` | STRING | desktop / mobile / tablet | Device analysis |
| `device.mobile_brand_name` | STRING |  |  |
| `device.mobile_model_name` | STRING |  |  |
| `device.mobile_marketing_name` | STRING |  |  |
| `device.mobile_os_hardware_model` | INTEGER |  |  |
| `device.operating_system` | STRING | Operating system | Device analysis |
| `device.operating_system_version` | STRING |  |  |
| `device.vendor_id` | INTEGER |  |  |
| `device.advertising_id` | INTEGER |  |  |
| `device.language` | STRING |  |  |
| `device.is_limited_ad_tracking` | STRING |  |  |
| `device.time_zone_offset_seconds` | INTEGER |  |  |
| `device.web_info` | RECORD |  |  |
| `device.web_info.browser` | STRING | Browser | QA, device analysis |
| `device.web_info.browser_version` | STRING |  |  |
| `geo` | RECORD |  |  |
| `geo.continent` | STRING |  |  |
| `geo.sub_continent` | STRING |  |  |
| `geo.country` | STRING | Country of the user | Geographic analysis |
| `geo.region` | STRING |  |  |
| `geo.city` | STRING | City of the user | Geographic analysis |
| `geo.metro` | STRING |  |  |
| `app_info` | RECORD |  |  |
| `app_info.id` | STRING |  |  |
| `app_info.version` | STRING |  |  |
| `app_info.install_store` | STRING |  |  |
| `app_info.firebase_app_id` | STRING |  |  |
| `app_info.install_source` | STRING |  |  |
| `traffic_source` | RECORD |  |  |
| `traffic_source.medium` | STRING | FIRST-EVER acquisition medium of the user | Acquisition |
| `traffic_source.name` | STRING | FIRST-EVER acquisition campaign of the user | Campaigns |
| `traffic_source.source` | STRING | FIRST-EVER acquisition source of the user (not the session) | Acquisition |
| `stream_id` | INTEGER |  |  |
| `platform` | STRING | WEB / ANDROID / IOS | Platform split |
| `event_dimensions` | RECORD |  |  |
| `event_dimensions.hostname` | STRING |  |  |
| `ecommerce` | RECORD |  |  |
| `ecommerce.total_item_quantity` | INTEGER | Units in the order | Basket size |
| `ecommerce.purchase_revenue_in_usd` | FLOAT |  |  |
| `ecommerce.purchase_revenue` | FLOAT | Order revenue | Revenue, AOV |
| `ecommerce.refund_value_in_usd` | FLOAT |  |  |
| `ecommerce.refund_value` | FLOAT |  |  |
| `ecommerce.shipping_value_in_usd` | FLOAT |  |  |
| `ecommerce.shipping_value` | FLOAT |  |  |
| `ecommerce.tax_value_in_usd` | FLOAT |  |  |
| `ecommerce.tax_value` | FLOAT |  |  |
| `ecommerce.unique_items` | INTEGER |  |  |
| `ecommerce.transaction_id` | STRING | Order ID | Transactions |
| `items` | REPEATED RECORD | Repeated product lines attached to ecommerce events | Product analysis |
| `items.item_id` | STRING | Product ID | Product analysis |
| `items.item_name` | STRING | Product name | Product analysis |
| `items.item_brand` | STRING |  |  |
| `items.item_variant` | STRING |  |  |
| `items.item_category` | STRING | Product category | Category analysis |
| `items.item_category2` | STRING |  |  |
| `items.item_category3` | STRING |  |  |
| `items.item_category4` | STRING |  |  |
| `items.item_category5` | STRING |  |  |
| `items.price_in_usd` | FLOAT |  |  |
| `items.price` | FLOAT | Unit price | Product revenue |
| `items.quantity` | INTEGER | Units | Product revenue |
| `items.item_revenue_in_usd` | FLOAT |  |  |
| `items.item_revenue` | FLOAT | Line revenue | Product revenue |
| `items.item_refund_in_usd` | FLOAT |  |  |
| `items.item_refund` | FLOAT |  |  |
| `items.coupon` | STRING |  |  |
| `items.affiliation` | STRING |  |  |
| `items.location_id` | STRING |  |  |
| `items.item_list_id` | STRING |  |  |
| `items.item_list_name` | STRING |  |  |
| `items.item_list_index` | STRING |  |  |
| `items.promotion_id` | STRING |  |  |
| `items.promotion_name` | STRING |  |  |
| `items.creative_name` | STRING |  |  |
| `items.creative_slot` | STRING |  |  |

## Modelling notes

- `traffic_source.*` is the user's **first-ever** acquisition source, not the session source.
  `stg_sessions` uses session-level `source`/`medium`/`campaign` params where present and
  falls back to first touch; `source_scope` records which one was used.
- `event_params` and `items` are repeated records and must be flattened with `UNNEST`.
- User counts are not additive across days or dimensions; recompute distinct users from
  `stg_sessions` for any total.
