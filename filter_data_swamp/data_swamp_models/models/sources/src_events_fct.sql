SELECT
    e._dlt_id AS event_key,
    e._dlt_parent_id AS session_key,
    s.visit_id AS session_id,
    s.full_visitor_id AS user_id,
    STRPTIME(
        CONCAT(
            SUBSTRING(s.date::TEXT, 1, 4), '-',
            SUBSTRING(s.date::TEXT, 5, 2), '-',
            SUBSTRING(s.date::TEXT, 7, 2), ' ',
            LPAD(e.hour::TEXT, 2, '0'), ':',
            LPAD(e.minute::TEXT, 2, '0'), ':00'
        ), '%Y-%m-%d %H:%M:%S'
    ) - INTERVAL '4' MONTH + INTERVAL '7' YEAR AS event_timestamp,
    e.hit_number AS event_number,
    e.type AS event_type,
    CASE
        WHEN e.page__page_path LIKE '%basket%' OR e.page__page_path LIKE '%cart%' OR e.page__page_path LIKE '%updatecart%' THEN 'shopping_cart'
        WHEN e.page__page_path LIKE '%revieworder%' OR e.page__page_path LIKE '%submitorder%' OR e.page__page_path LIKE '%checkout%' THEN 'checkout'
        WHEN e.page__page_path LIKE '%ordercompleted%' THEN 'order_completed'
        WHEN e.page__page_path LIKE '/google+redesign/%' THEN 'product_category_viewed'
        ELSE 'other'
    END AS funnel_position,
    -- Simplified product_category_viewed extraction
    CASE
        WHEN e.page__page_path LIKE '/google+redesign/%' 
        THEN SPLIT_PART(REPLACE(e.page__page_path, '/google+redesign/', ''), '/', 1)
        ELSE NULL
    END AS product_category_viewed,
    e.page__page_path AS event_page_path,
    e.e_commerce_action__action_type AS ecommerce_event_type,
    e.is_entrance,
    e.is_exit,
    e.is_interaction
FROM {{ source('duck_pond', 'load') }} s
JOIN {{ source('duck_pond', 'load__hits') }} e
    ON s._dlt_id = e._dlt_parent_id

{% if is_incremental() %}
WHERE 
    (STRPTIME(
        CONCAT(
            SUBSTRING(s.date::TEXT, 1, 4), '-',
            SUBSTRING(s.date::TEXT, 5, 2), '-',
            SUBSTRING(s.date::TEXT, 7, 2), ' ',
            LPAD(e.hour::TEXT, 2, '0'), ':',
            LPAD(e.minute::TEXT, 2, '0'), ':00'
        ), '%Y-%m-%d %H:%M:%S'
    )- INTERVAL '4' MONTH + INTERVAL '7' YEAR) > (SELECT MAX(t.event_timestamp) FROM {{ this }} t)
{% endif %}