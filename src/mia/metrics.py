"""Deterministic KPI layer. Every rate is computed here, never by the LLM."""
import pandas as pd

# name: (numerator, denominator, multiplier)
RATE_DEFS = {
    "conversion_rate": ("converting_sessions", "sessions", 100),
    "engagement_rate": ("engaged_sessions", "sessions", 100),
    "view_to_cart_rate": ("sessions_with_add_to_cart", "sessions_with_product_view", 100),
    "cart_to_checkout_rate": ("sessions_with_checkout", "sessions_with_add_to_cart", 100),
    "checkout_to_purchase_rate": ("converting_sessions", "sessions_with_checkout", 100),
    "aov": ("revenue", "transactions", 1),
    "revenue_per_session": ("revenue", "sessions", 1),
    "new_user_share": ("new_users", "users", 100),
}

FUNNEL_STEPS = {
    "view_to_cart_rate": "Product view -> add to cart",
    "cart_to_checkout_rate": "Add to cart -> checkout",
    "checkout_to_purchase_rate": "Checkout -> purchase",
}

KPI_FIELDS = [
    "revenue", "transactions", "sessions", "users", "new_users", "conversion_rate", "aov",
    "revenue_per_session", "engagement_rate", "new_user_share",
]


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for name, (num, den, mult) in RATE_DEFS.items():
        denominator = df[den].astype(float)
        df[name] = df[num].astype(float).div(denominator.where(denominator > 0)) * mult
    return df


def complete_weeks(weekly: pd.DataFrame) -> list:
    """Weeks where the total row covers all 7 days (drops partial first/last weeks)."""
    total = weekly[weekly["dimension"] == "total"]
    return sorted(pd.to_datetime(total.loc[total["days_in_data"] >= 7, "week_start"]).tolist())


def pct_change(cur, prev):
    if prev is None or pd.isna(prev) or prev == 0 or cur is None or pd.isna(cur):
        return None
    return (cur - prev) / prev * 100
