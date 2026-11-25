-- ============================================================================
-- Agoda / OTA Hotel Booking Funnel & A/B Experiment SQL Analysis
-- Dialect: PostgreSQL / SQLite Compatible
-- ============================================================================

-- 1. End-to-End Funnel Conversion & Step-to-Step Drop-Off by Device
WITH device_funnel AS (
    SELECT
        device,
        COUNT(*) AS total_sessions,
        SUM(viewed_hotel) AS hotel_views,
        SUM(started_checkout) AS checkouts,
        SUM(completed_booking) AS bookings
    FROM ota_sessions
    GROUP BY device
)
SELECT
    device,
    total_sessions,
    ROUND(100.0 * hotel_views / total_sessions, 2) AS search_to_view_pct,
    ROUND(100.0 * checkouts / NULLIF(hotel_views, 0), 2) AS view_to_checkout_pct,
    ROUND(100.0 * bookings / NULLIF(checkouts, 0), 2) AS checkout_to_book_pct,
    ROUND(100.0 * bookings / total_sessions, 2) AS overall_cvr_pct
FROM device_funnel
ORDER BY overall_cvr_pct DESC;


-- 2. A/B Test Experiment Performance & Revenue Per Session (RPS)
SELECT
    experiment_group,
    COUNT(*) AS total_sessions,
    SUM(started_checkout) AS checkout_starts,
    SUM(completed_booking) AS completed_bookings,
    ROUND(100.0 * SUM(completed_booking) / COUNT(*), 3) AS overall_cvr_pct,
    ROUND(100.0 * SUM(completed_booking) / NULLIF(SUM(started_checkout), 0), 2) AS checkout_cvr_pct,
    ROUND(AVG(CASE WHEN completed_booking = 1 THEN booking_value_usd END), 2) AS avg_order_value_usd,
    ROUND(SUM(CASE WHEN completed_booking = 1 THEN booking_value_usd ELSE 0 END) / COUNT(*), 2) AS revenue_per_session_usd
FROM ota_sessions
GROUP BY experiment_group;


-- 3. Country-Level Market Share & Revenue Contribution (Window Function)
WITH country_revenue AS (
    SELECT
        country,
        COUNT(*) AS sessions,
        SUM(completed_booking) AS bookings,
        ROUND(SUM(CASE WHEN completed_booking = 1 THEN booking_value_usd ELSE 0 END), 2) AS total_gmv_usd
    FROM ota_sessions
    GROUP BY country
)
SELECT
    country,
    sessions,
    bookings,
    ROUND(100.0 * bookings / sessions, 2) AS cvr_pct,
    total_gmv_usd,
    ROUND(100.0 * total_gmv_usd / SUM(total_gmv_usd) OVER (), 2) AS gmv_share_pct
FROM country_revenue
ORDER BY total_gmv_usd DESC;


-- 4. Segment Lift Analysis: Experiment Group x Device Type
SELECT
    device,
    experiment_group,
    COUNT(*) AS sessions,
    SUM(completed_booking) AS bookings,
    ROUND(100.0 * SUM(completed_booking) / NULLIF(SUM(started_checkout), 0), 2) AS checkout_completion_pct,
    ROUND(100.0 * SUM(completed_booking) / COUNT(*), 2) AS overall_cvr_pct
FROM ota_sessions
GROUP BY device, experiment_group
ORDER BY device, experiment_group;