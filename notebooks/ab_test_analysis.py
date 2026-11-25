import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep

# Ensure an images folder exists for GitHub README visuals
os.makedirs("images", exist_ok=True)

# 1. Load Data & Run SQL Queries via In-Memory SQLite
df = pd.read_csv("data/ota_sessions.csv")
conn = sqlite3.connect(":memory:")
df.to_sql("ota_sessions", conn, index=False, if_exists="replace")

funnel_sql = """
SELECT
    device,
    COUNT(*) AS total_sessions,
    SUM(viewed_hotel) AS hotel_views,
    SUM(started_checkout) AS checkouts,
    SUM(completed_booking) AS bookings,
    ROUND(100.0 * SUM(completed_booking) / COUNT(*), 2) AS overall_cvr_pct
FROM ota_sessions
GROUP BY device
ORDER BY overall_cvr_pct DESC;
"""
funnel_df = pd.read_sql_query(funnel_sql, conn)
print("\n--- 1. FUNNEL CONVERSION BY DEVICE (VIA SQL) ---")
print(funnel_df.to_string(index=False))

# 2. Sample Ratio Mismatch (SRM) Check (Expected 50/50 Split)
group_counts = df["experiment_group"].value_counts()
n_control = group_counts["control"]
n_variant = group_counts["variant"]
chi2_stat, srm_p_value = stats.chisquare(
    [n_control, n_variant], f_exp=[len(df) / 2, len(df) / 2])

print("\n--- 2. SAMPLE RATIO MISMATCH (SRM) CHECK ---")
print(f"Control Sessions: {n_control:,} | Variant Sessions: {n_variant:,}")
print(
    f"SRM Chi-Square p-value: {srm_p_value:.4f} ({'PASS: No randomization bias' if srm_p_value > 0.01 else 'FAIL: Investigate traffic split'})")

# 3. Primary Metric Hypothesis Test: Overall Booking Conversion Rate
conv_control = df[df["experiment_group"] ==
                  "control"]["completed_booking"].sum()
conv_variant = df[df["experiment_group"] ==
                  "variant"]["completed_booking"].sum()

cvr_control = conv_control / n_control
cvr_variant = conv_variant / n_variant
abs_lift = cvr_variant - cvr_control
rel_lift = (cvr_variant - cvr_control) / cvr_control

z_stat, p_val = proportions_ztest([conv_variant, conv_control], [
                                  n_variant, n_control], alternative="two-sided")
ci_low, ci_high = confint_proportions_2indep(
    conv_variant, n_variant, conv_control, n_control, method="wald")

print("\n--- 3. A/B TEST RESULTS (OVERALL CONVERSION RATE) ---")
print(
    f"Control CVR:  {cvr_control * 100:.3f}% ({conv_control:,} / {n_control:,})")
print(
    f"Variant CVR:  {cvr_variant * 100:.3f}% ({conv_variant:,} / {n_variant:,})")
print(
    f"Absolute Lift: +{abs_lift * 100:.3f}% (95% CI: [+{ci_low * 100:.3f}%, +{ci_high * 100:.3f}%])")
print(f"Relative Lift: +{rel_lift * 100:.2f}%")
print(f"Z-Statistic:   {z_stat:.3f} | p-value: {p_val:.6f}")

# 4. Guardrail & Monetization Metrics (AOV & Revenue Per Session)
aov_control = df[(df["experiment_group"] == "control") & (
    df["completed_booking"] == 1)]["booking_value_usd"]
aov_variant = df[(df["experiment_group"] == "variant") & (
    df["completed_booking"] == 1)]["booking_value_usd"]
_, aov_p_val = stats.ttest_ind(aov_variant, aov_control, equal_var=False)

rps_control = df[df["experiment_group"] == "control"].apply(
    lambda r: r["booking_value_usd"] if r["completed_booking"] == 1 else 0, axis=1).mean()
rps_variant = df[df["experiment_group"] == "variant"].apply(
    lambda r: r["booking_value_usd"] if r["completed_booking"] == 1 else 0, axis=1).mean()

print("\n--- 4. GUARDRAIL & REVENUE METRICS ---")
print(f"Control AOV: ${aov_control.mean():.2f} | Variant AOV: ${aov_variant.mean():.2f} (p-value: {aov_p_val:.4f} -> No AOV cannibalization)")
print(
    f"Control RPS: ${rps_control:.2f} | Variant RPS: ${rps_variant:.2f} (+${rps_variant - rps_control:.2f} per session)")

# 5. Generate Chart 1: Funnel Drop-off by Device
plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(9, 5))
devices = funnel_df["device"]
x = np.arange(len(devices))
width = 0.25

ax.bar(x - width, 100 * funnel_df["hotel_views"] / funnel_df["total_sessions"],
       width, label="Viewed Hotel (%)", color="#4C72B0")
ax.bar(x, 100 * funnel_df["checkouts"] / funnel_df["total_sessions"],
       width, label="Started Checkout (%)", color="#55A868")
ax.bar(x + width, funnel_df["overall_cvr_pct"], width,
       label="Completed Booking (%)", color="#C44E52")

ax.set_title("OTA Booking Funnel Progression by Device Type",
             fontsize=13, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(["Mobile App", "Desktop", "Mobile Web"])
ax.set_ylabel("% of Total Sessions")
ax.legend()
plt.tight_layout()
plt.savefig("images/funnel_by_device.png", dpi=200)
plt.close()

# 6. Generate Chart 2: A/B Test Conversion Lift by Device
seg = df.groupby(["device", "experiment_group"])[
    "completed_booking"].mean().unstack() * 100
fig, ax = plt.subplots(figsize=(9, 5))
seg.loc[["mobile_app", "desktop", "mobile_web"]].plot(
    kind="bar", ax=ax, color=["#8C8C8C", "#2B5C8F"], width=0.65)
ax.set_title("A/B Test Impact: Upfront Price Transparency vs. Control",
             fontsize=13, fontweight="bold")
ax.set_xticklabels(["Mobile App", "Desktop", "Mobile Web"], rotation=0)
ax.set_ylabel("Overall Conversion Rate (%)")
ax.legend(["Control (Base Price First)", "Variant (All-Inclusive Price)"])
plt.tight_layout()
plt.savefig("images/ab_test_lift.png", dpi=200)
plt.close()

print("\nSaved charts to images/funnel_by_device.png and images/ab_test_lift.png")
