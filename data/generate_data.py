import numpy as np
import pandas as pd

np.random.seed(42)
n_sessions = 100_000

df = pd.DataFrame({
    "session_id": range(1, n_sessions + 1),
    "user_id": np.random.randint(10000, 55000, size=n_sessions),
    "experiment_group": np.random.choice(["control", "variant"], size=n_sessions, p=[0.5, 0.5]),
    "device": np.random.choice(["mobile_app", "mobile_web", "desktop"], size=n_sessions, p=[0.45, 0.35, 0.20]),
    "country": np.random.choice(["TH", "SG", "MY", "BD", "JP"], size=n_sessions, p=[0.30, 0.20, 0.20, 0.15, 0.15]),
    "booking_value_usd": np.round(np.random.lognormal(mean=4.8, sigma=0.6, size=n_sessions), 2)
})

# Funnel progression probabilities
df["viewed_hotel"] = np.random.binomial(1, 0.62, n_sessions)
df["started_checkout"] = np.where(
    df["viewed_hotel"] == 1, np.random.binomial(1, 0.28, n_sessions), 0)

# Variant reduces surprise tax/fee drop-off at checkout (+4.0% absolute checkout completion lift)
conv_prob = np.where(df["experiment_group"] == "variant", 0.44, 0.40)
conv_prob = np.where(df["device"] == "mobile_web",
                     conv_prob * 0.75, conv_prob)  # Mobile web friction

df["completed_booking"] = np.where(
    df["started_checkout"] == 1,
    np.random.binomial(1, conv_prob),
    0
)

df.to_csv("data/ota_sessions.csv", index=False)
print("Saved 100,000 sessions to data/ota_sessions.csv")
