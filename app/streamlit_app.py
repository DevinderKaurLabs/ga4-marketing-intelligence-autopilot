"""GA4 Marketing Intelligence Autopilot: dashboard + manager assistant.
Reads the pipeline's saved outputs (no BigQuery at runtime). Styled to match devinder-kaur.vercel.app."""
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mia import theme  # noqa: E402
from mia.store import Store  # noqa: E402

C = theme.COLORS
st.set_page_config(page_title="GA4 Marketing Intelligence Autopilot", page_icon="📈", layout="wide")

# Secrets (Streamlit Cloud) -> environment, so the shared LLM client picks them up
try:
    for key in ("LLM_PROVIDER", "LLM_API_KEY", "ASSISTANT_MODEL", "APP_PASSCODE"):
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass

st.markdown(f"""
<style>
@import url('{theme.GOOGLE_FONTS_URL}');
h1, h2, h3, h4 {{ font-family: {theme.STACK_HEADING} !important; font-weight: 500 !important; color: {C['navy']}; }}
p, li, label, td, th, .stMarkdown, .stCaption {{ font-family: {theme.STACK_BODY}; }}
[data-testid="stMetricValue"] {{ font-family: {theme.STACK_HEADING}; color: {C['navy']}; }}
[data-testid="stMetricLabel"] p {{ color: {C['teal_ink']}; }}
.mark {{ font-family: {theme.STACK_SCRIPT}; font-size: 2.1rem; color: {C['navy']}; line-height: 1.1; }}
.headline {{ font-family: {theme.STACK_HEADING}; font-size: 1.7rem; line-height: 1.25; color: {C['navy']};
             max-width: 46ch; margin: .2rem 0 1rem; }}
.pill {{ display:inline-block; font-size:.8rem; font-weight:700; padding:1px 10px; border-radius:999px; margin-right:6px; }}
.sev-critical {{ background:{C['navy']}; color:{C['white']}; }}
.sev-warning {{ background:{C['teal']}; color:{C['white']}; }}
.sev-watch {{ background:{C['sky']}; color:{C['navy']}; }}
.sev-positive {{ background:{C['white']}; color:{C['teal_ink']}; border:1px solid {C['teal']}; }}
.trust {{ background:{C['navy']}; color:{C['white']}; padding:14px 18px; border-radius:4px; font-size:.92rem; }}
.trust b {{ color:{C['sky']}; font-family:{theme.STACK_HEADING}; font-weight:500; }}
.note {{ color:{C['teal_ink']}; font-size:.9rem; }}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def get_store():
    return Store()


store = get_store()
if not store.weeks:
    st.error("No pipeline outputs found in artifacts/. Run the intelligence engine first.")
    st.stop()

TEMPLATE = theme.plotly_template()


def fig_base(fig, height=320, title=None):
    fig.update_layout(template=TEMPLATE, height=height, title=title, showlegend=fig.layout.showlegend)
    return fig


def money(v):
    return "n/a" if v is None else f"${v:,.0f}"


def pct(v):
    return "n/a" if v is None else f"{v:+.1f}%"


# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown('<div class="mark">Autopilot</div>', unsafe_allow_html=True)
    st.caption("GA4 Marketing Intelligence")
    week = st.selectbox("Week (Monday)", store.weeks, index=len(store.weeks) - 1)
    page = st.radio("View", ["Overview", "Acquisition", "Customers", "Products", "Signals & history",
                             "Weekly brief", "Ask the data"])
    st.divider()
    st.caption("Architecture demonstration on Google's public GA4 sample (Google Merchandise Store, "
               "Nov 2020 to Jan 2021). Numbers computed in SQL/Python; AI writes, a validator checks.")
    if store.primary_model:
        st.caption(f"Brief model: {store.primary_model}")

P = store.payloads[week]
K = P["kpis"]
brief = store.brief(week)


def kpi_row():
    cols = st.columns(5)
    items = [("Revenue", "revenue", money), ("Transactions", "transactions", lambda v: f"{v:,}"),
             ("Conversion rate", "conversion_rate", lambda v: f"{v:.2f}%"),
             ("Avg order value", "aov", lambda v: f"${v:,.2f}"), ("Sessions", "sessions", lambda v: f"{v:,}")]
    for col, (label, key, fmt) in zip(cols, items):
        k = K[key]
        col.metric(label, fmt(k["current"]), pct(k["change_pct"]) if k["change_pct"] is not None else None)


def revenue_chart():
    r = store.runs
    if r.empty:
        return
    colors = theme.highlight_colors(len(r), list(r["week_start"]).index(week) if week in list(r["week_start"]) else -1)
    fig = go.Figure(go.Bar(x=r["week_start"], y=r["revenue"], marker_color=colors,
                           hovertemplate="%{x}<br>Revenue $%{y:,.0f}<extra></extra>"))
    fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    st.plotly_chart(fig_base(fig, 300, "Weekly revenue (selected week in navy)"), width="stretch")


def change_bars(rows, label_key="name", value_key="revenue_change_pct", title=""):
    df = pd.DataFrame(rows)
    if df.empty or value_key not in df:
        st.info("No data for this view.")
        return
    df = df.dropna(subset=[value_key])
    colors = [C["navy"] if v < 0 else C["teal"] for v in df[value_key]]
    fig = go.Figure(go.Bar(x=df[value_key], y=df[label_key], orientation="h", marker_color=colors,
                           hovertemplate="%{y}: %{x:+.1f}%<extra></extra>"))
    fig.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor=C["rule"])
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_base(fig, 60 + 38 * len(df), title), width="stretch")


def severity_pill(sev):
    return f'<span class="pill sev-{sev}">{sev.capitalize()}</span>'


# ---------------- pages ----------------
if page == "Overview":
    st.markdown(f"#### Week of {week} &nbsp;·&nbsp; <span class='note'>vs {P['run']['previous_week_start']}"
                + (f" · {', '.join(e.split(': ', 1)[-1] for e in P['calendar_events']['this_week'])}"
                   if P["calendar_events"]["this_week"] else "") + "</span>", unsafe_allow_html=True)
    headline = brief["brief"]["headline"] if brief else (
        store.runs.set_index("week_start").loc[week, "headline"] if not store.runs.empty else "")
    st.markdown(f'<div class="headline">{headline}</div>', unsafe_allow_html=True)
    kpi_row()
    revenue_chart()
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("What changed")
        if brief:
            for ch in brief["brief"]["what_changed"]:
                st.markdown(f"{severity_pill(ch['severity'])} **{ch['title']}.** {ch['detail']}",
                            unsafe_allow_html=True)
        else:
            for r in P["anomalies"]["risks"][:5]:
                where = "" if r["dimension"] == "total" else f" ({r['dimension']}: {r['dimension_value']})"
                st.markdown(f"{severity_pill(r['severity'])} {r['metric_label']}{where}: {r['change_pct']:+.1f}%",
                            unsafe_allow_html=True)
    with right:
        st.subheader("Actions")
        if brief:
            for a in brief["brief"]["actions"]:
                st.markdown(f"**{a['priority'].capitalize()}**: {a['action']}  \n"
                            f"<span class='note'>{a['owner']} · Evidence: {a['evidence']}</span>",
                            unsafe_allow_html=True)
        else:
            st.info("Briefs not generated yet for this week.")
    if brief:
        ok = brief["status"] == "validated"
        st.markdown(f"<div class='trust'><b>Trust check</b><br>"
                    + (f"Written by {brief['model']} and checked by the number validator: "
                       f"{brief['numbers_checked']} numbers checked, none invented."
                       if ok else "The AI draft failed validation, so this week shows the deterministic fallback.")
                    + "</div>", unsafe_allow_html=True)

elif page == "Acquisition":
    st.subheader(f"Acquisition, week of {week}")
    tabs = st.tabs(["Channels", "Devices", "Countries", "Campaigns"])
    for tab, key, label in zip(tabs, ["channels", "devices", "countries", "campaigns"],
                               ["channel", "device", "country", "campaign"]):
        with tab:
            rows = P.get(key, [])
            change_bars(rows, title=f"Revenue change vs previous week by {label}")
            if rows:
                df = pd.DataFrame(rows).rename(columns={"name": label.capitalize()})
                st.dataframe(df, hide_index=True, width="stretch")
    st.caption("Obfuscated placeholders such as <Other> and (data deleted) are shown for completeness "
               "but are never used for alerts or recommendations.")

elif page == "Customers":
    st.subheader(f"Customers, week of {week}")
    cw = P["customers"]["this_week"]
    cols = st.columns(4)
    for col, (label, key) in zip(cols, [("Purchasers", "purchasers"), ("New purchasers", "new_purchasers"),
                                        ("Returning purchasers", "returning_purchasers"),
                                        ("Returning revenue share", "returning_revenue_share_pct")]):
        k = cw.get(key)
        if k:
            val = f"{k['current']:.1f}%" if "pct" in key else f"{k['current']:,}"
            col.metric(label, val, pct(k["change_pct"]) if k["change_pct"] is not None else None)
    seg = pd.DataFrame(P["customers"]["rfm_segments"])
    if not seg.empty:
        idx = int(seg["customers_change"].abs().idxmax())
        fig = go.Figure(go.Bar(x=seg["segment"], y=seg["customers"], marker_color=theme.highlight_colors(len(seg), idx),
                               customdata=seg["customers_change"],
                               hovertemplate="%{x}<br>%{y:,} customers (%{customdata:+} vs last week)<extra></extra>"))
        st.plotly_chart(fig_base(fig, 320, "RFM segments (biggest weekly move in navy)"), width="stretch")
        st.dataframe(seg[["segment", "description", "customers", "customers_change", "avg_spend",
                          "avg_recency_days"]], hide_index=True, width="stretch")
        st.caption(f"High-value threshold: ${P['customers']['rfm_high_value_threshold']} lifetime spend "
                   "within the observed window.")

elif page == "Products":
    st.subheader(f"Products, week of {week}")
    pr = P["products"]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Biggest gainers**")
        st.dataframe(pd.DataFrame(pr["top_gainers"]), hide_index=True, width="stretch")
    with c2:
        st.markdown("**Biggest decliners**")
        st.dataframe(pd.DataFrame(pr["top_decliners"]), hide_index=True, width="stretch")
    st.markdown("**Viewed a lot, rarely bought**")
    low = pd.DataFrame(pr["high_interest_low_conversion"])
    st.dataframe(low, hide_index=True, width="stretch")
    if not low.empty and "check_tracking" in low and low["check_tracking"].any():
        st.caption("Rows flagged check_tracking have many add-to-carts and zero purchases: usually item "
                   "mapping or tracking, not demand. Verify before acting.")
    cats = pd.DataFrame(pr["categories"])
    if not cats.empty:
        fig = go.Figure([go.Bar(name="Previous week", x=cats["item_category"], y=cats["revenue_prev"],
                                marker_color=C["teal"]),
                         go.Bar(name="This week", x=cats["item_category"], y=cats["revenue_cur"],
                                marker_color=C["navy"])])
        fig.update_layout(barmode="group", showlegend=True)
        fig.update_yaxes(tickprefix="$", tickformat=",.0f")
        st.plotly_chart(fig_base(fig, 340, "Category revenue"), width="stretch")

elif page == "Signals & history":
    st.subheader("Signals across all weeks")
    a = store.anomalies.copy()
    if a.empty:
        st.info("No signals stored.")
    else:
        f1, f2, f3 = st.columns(3)
        sev = f1.multiselect("Severity", ["critical", "warning", "watch"], default=["critical", "warning"])
        direction = f2.selectbox("Direction", ["risks (down)", "upside (up)", "both"])
        dims = f3.multiselect("Dimension", sorted(a["dimension"].unique()), default=sorted(a["dimension"].unique()))
        a = a[a["severity"].isin(sev) & a["dimension"].isin(dims)]
        if direction != "both":
            a = a[a["direction"] == ("down" if direction.startswith("risks") else "up")]
        show = a[["week_start", "severity", "direction", "dimension", "dimension_value", "metric_label",
                  "previous_value", "current_value", "change_pct"]].copy()
        show[["previous_value", "current_value", "change_pct"]] = show[["previous_value", "current_value",
                                                                         "change_pct"]].round(2)
        st.dataframe(show.sort_values(["week_start", "severity"]), hide_index=True, width="stretch")

    st.subheader("Trend")
    snap = store.snapshots
    if not snap.empty:
        options = {"Revenue": "revenue", "Sessions": "sessions", "Conversion rate": "conversion_rate",
                   "Average order value": "aov", "Cart to checkout rate": "cart_to_checkout_rate",
                   "Product view to cart rate": "view_to_cart_rate"}
        label = st.selectbox("Metric", list(options))
        t = snap[(snap["dimension"] == "total") & (snap["metric"] == options[label])].sort_values("week_start")
        fig = go.Figure(go.Scatter(x=t["week_start"], y=t["value"], mode="lines+markers",
                                   line=dict(color=C["navy"], width=2.5), marker=dict(color=C["navy"], size=7)))
        sel = t[t["week_start"] == week]
        if not sel.empty:
            fig.add_trace(go.Scatter(x=sel["week_start"], y=sel["value"], mode="markers",
                                     marker=dict(color=C["teal"], size=14, line=dict(color=C["navy"], width=2)),
                                     hoverinfo="skip"))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig_base(fig, 320, f"{label}, all weeks (selected week ringed)"), width="stretch")

    st.subheader("Run history")
    if not store.runs.empty:
        cols = [c for c in ["week_start", "revenue", "revenue_change_pct", "n_critical", "n_warning", "n_watch",
                            "headline"] if c in store.runs]
        st.dataframe(store.runs[cols], hide_index=True, width="stretch")
    st.subheader("Data quality")
    for n in P["data_quality"]["notes"]:
        st.markdown(f"- {n}")

elif page == "Weekly brief":
    st.subheader(f"Weekly brief, week of {week}")
    html, pdf = store.brief_html(week)
    if html:
        if pdf:
            st.download_button("Download PDF", pdf.read_bytes(), file_name=pdf.name, mime="application/pdf")
        # The brief is rendered by Jinja with autoescaping, so model text cannot inject markup or scripts.
        st.iframe(html, height=1650)
    else:
        st.info("No brief generated for this week yet.")
    ev = store.eval_runs()
    if not ev.empty:
        st.subheader("Model evaluation")
        summary = (ev.assign(validated=ev["status"].eq("validated"))
                     .groupby("model").agg(weeks=("week_start", "count"), validated=("validated", "mean"),
                                           first_try_pass=("first_try_pass", "mean"),
                                           invented_first_try=("invented_numbers_first_try", "mean"),
                                           avg_latency_s=("latency_s", "mean")))
        summary[["validated", "first_try_pass"]] = (summary[["validated", "first_try_pass"]] * 100).round(0)
        st.dataframe(summary.round(1).rename(columns={"validated": "validated %", "first_try_pass": "first try %"}),
                     width="stretch")
        st.caption("Same payloads, prompt and validator for every model. Invented numbers are caught and sent "
                   "back; a brief that never validates falls back to the deterministic version.")

elif page == "Ask the data":
    st.subheader("Ask the data")
    st.markdown("<span class='note'>The assistant picks read-only data tools, then answers. Every number in "
                "the answer is checked against the data it retrieved.</span>", unsafe_allow_html=True)
    model = os.getenv("ASSISTANT_MODEL") or store.primary_model
    if not os.getenv("LLM_API_KEY") or not model:
        st.info("The assistant is offline in this deployment (no model key configured). "
                "All other views work without it.")
        st.stop()
    passcode = os.getenv("APP_PASSCODE")
    if passcode and st.session_state.get("unlocked") is not True:
        if st.text_input("Passcode", type="password") == passcode:
            st.session_state["unlocked"] = True
            st.rerun()
        st.stop()
    st.session_state.setdefault("asked", 0)
    examples = ["Why did revenue fall in the week of 21 December?", "Which segments need attention this week?",
                "What were the three biggest risks across all weeks?", "How did returning customers behave this week?"]
    cols = st.columns(len(examples))
    clicked = None
    for col, ex in zip(cols, examples):
        if col.button(ex, width="stretch"):
            clicked = ex
    q = st.chat_input("Ask about revenue, channels, customers, products...") or clicked
    if q:
        if st.session_state["asked"] >= 15:
            st.warning("Question limit for this session reached.")
            st.stop()
        st.session_state["asked"] += 1
        from mia.assistant import ask

        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            with st.spinner("Looking at the data..."):
                try:
                    res = ask(store, q, week, model)
                except Exception as exc:
                    res = {"ok": False, "error": str(exc)[:200], "tool_results": {}}
            if res["ok"]:
                ans = res["answer"]
                st.markdown(ans["answer"])
                if ans.get("evidence"):
                    st.markdown("**Evidence**\n" + "\n".join(f"- {e}" for e in ans["evidence"]))
                if ans.get("likely_drivers"):
                    st.markdown("**Likely drivers**\n" + "\n".join(f"- {d}" for d in ans["likely_drivers"]))
                if ans.get("recommended_action"):
                    st.markdown(f"**Recommended action:** {ans['recommended_action']}")
                st.caption(f"Verified: {res['numbers_checked']} numbers checked against the retrieved data. "
                           f"Tools used: {', '.join(k.split('(')[0] for k in res['tool_results'])}.")
            else:
                st.warning("I couldn't produce an answer I can verify, so here is the underlying data instead.")
                if res.get("error"):
                    st.caption(res["error"])
            with st.expander("Data retrieved"):
                st.json(res.get("tool_results", {}))
