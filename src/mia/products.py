"""Product intelligence: movers, high-interest/low-conversion products, categories."""
import pandas as pd

UNUSABLE = {"", "(not set)", "<Other>", "(data deleted)"}


def weekly_products(daily: pd.DataFrame) -> pd.DataFrame:
    df = daily.copy()
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    return (df.groupby(["week_start", "item_name", "item_category"], dropna=False)
              [["views", "adds_to_cart", "purchase_lines", "units", "item_revenue"]]
              .sum().reset_index())


def product_insights(wp: pd.DataFrame, week, prev_week, top_n: int = 5) -> dict:
    wp = wp[~wp["item_name"].fillna("").isin(UNUSABLE)]
    agg = ["views", "adds_to_cart", "purchase_lines", "units", "item_revenue"]
    cur = wp[wp["week_start"] == week].groupby("item_name")[agg].sum()
    prev = wp[wp["week_start"] == prev_week].groupby("item_name")[agg].sum()
    m = cur.join(prev, how="outer", lsuffix="_cur", rsuffix="_prev").fillna(0)
    m["revenue_delta"] = m["item_revenue_cur"] - m["item_revenue_prev"]
    material = m[(m["item_revenue_cur"] >= 200) | (m["item_revenue_prev"] >= 200)]
    cols = ["item_revenue_cur", "item_revenue_prev", "revenue_delta", "views_cur", "units_cur"]
    gainers = material[material["revenue_delta"] > 0].nlargest(top_n, "revenue_delta")[cols]
    decliners = material[material["revenue_delta"] < 0].nsmallest(top_n, "revenue_delta")[cols]

    viewed = m[m["views_cur"] >= max(200, m["views_cur"].quantile(0.9))].copy()
    viewed["view_to_purchase_pct"] = viewed["purchase_lines_cur"] / viewed["views_cur"] * 100
    low_conv = viewed.nsmallest(top_n, "view_to_purchase_pct")[
        ["views_cur", "adds_to_cart_cur", "purchase_lines_cur", "view_to_purchase_pct"]]

    cats = wp.copy()
    cats["item_category"] = cats["item_category"].fillna("(not set)")
    c_cur = cats[cats["week_start"] == week].groupby("item_category")["item_revenue"].sum()
    c_prev = cats[cats["week_start"] == prev_week].groupby("item_category")["item_revenue"].sum()
    catdf = pd.concat({"revenue_cur": c_cur, "revenue_prev": c_prev}, axis=1).fillna(0)
    catdf = catdf.nlargest(8, "revenue_cur")

    def records(df):
        return df.reset_index().to_dict("records")

    return {"top_gainers": records(gainers), "top_decliners": records(decliners),
            "high_interest_low_conversion": records(low_conv), "categories": records(catdf)}
