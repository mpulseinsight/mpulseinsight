"""
mPulseInsight Pro Terminal v4.0
Production Streamlit Dashboard — Real Schema Edition
"""

import streamlit as st
import pandas as pd
import psycopg2
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# 1. PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="mPulse Pro Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚡"
)

# ─────────────────────────────────────────────
# 2. GLOBAL CSS — Dark Terminal Theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Barlow+Condensed:wght@400;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: #080c10 !important;
    color: #cfd8dc !important;
}
.stApp { background-color: #080c10; }
header[data-testid="stHeader"] { background: #080c10; border-bottom: 1px solid #1e2d3d; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0b1016 !important;
    border-right: 1px solid #1e2d3d !important;
}
[data-testid="stSidebar"] * { color: #90a4ae !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #eceff1 !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    letter-spacing: 0.08em;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #0d1821;
    border: 1px solid #1e2d3d;
    border-radius: 4px;
    padding: 12px 16px !important;
}
[data-testid="stMetricLabel"] p { font-size: 9px !important; letter-spacing: 0.12em; color: #37474f !important; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-family: 'Barlow Condensed', sans-serif !important; color: #eceff1 !important; }
[data-testid="stMetricDelta"] { font-size: 10px !important; }

/* ── Section headers ── */
h1 { font-family: 'Barlow Condensed', sans-serif !important; letter-spacing: 0.06em; color: #eceff1 !important; }
h2 { font-family: 'Barlow Condensed', sans-serif !important; letter-spacing: 0.05em; color: #b0bec5 !important; font-size: 1.1rem !important; }
h3 { font-family: 'Barlow Condensed', sans-serif !important; color: #78909c !important; font-size: 0.95rem !important; }

/* ── Inputs & selects ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] div {
    background: #0d1821 !important;
    border: 1px solid #1e2d3d !important;
    color: #cfd8dc !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    border-radius: 3px !important;
}
[data-testid="stSlider"] { accent-color: #00e676; }

/* ── Dataframe / table ── */
[data-testid="stDataFrame"] { border: 1px solid #1e2d3d; border-radius: 4px; }
thead tr th { background: #0d1821 !important; color: #37474f !important; font-size: 10px !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }
tbody tr:hover td { background: rgba(0,230,118,0.04) !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #455a64 !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #00e676 !important;
    border-bottom-color: #00e676 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0d1821 !important;
    border: 1px solid #1e2d3d !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary { font-size: 11px !important; color: #546e7a !important; }

/* ── Divider ── */
hr { border-color: #1e2d3d !important; }

/* ── Custom cards ── */
.intel-card {
    background: #0d1821;
    border: 1px solid #1e2d3d;
    border-radius: 6px;
    padding: 16px 18px;
    margin-bottom: 12px;
}
.regime-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 2px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.sig-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 2px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
}
.kpi-row { display: flex; gap: 8px; margin-bottom: 16px; }
.kpi-box {
    flex: 1;
    background: #0d1821;
    border: 1px solid #1e2d3d;
    border-bottom: 3px solid #1a3a4a;
    border-radius: 4px;
    padding: 10px 14px;
    text-align: center;
}
.kpi-label { font-size: 8px; color: #37474f; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px; }
.kpi-val { font-size: 18px; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; color: #eceff1; }
.factor-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #0f1e2a; }
.factor-label { font-size: 9px; color: #546e7a; letter-spacing: 0.08em; }
.factor-bar-bg { background: rgba(255,255,255,0.04); height: 3px; border-radius: 2px; margin-top: 3px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #00e676; display: inline-block; margin-right: 6px; box-shadow: 0 0 6px rgba(0,230,118,0.5); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 3. HELPERS
# ─────────────────────────────────────────────
SIGNAL_COLORS = {
    "HIGH CONVICTION BUY": "#00e676",
    "BULLISH":             "#69f0ae",
    "NEUTRAL":             "#ffd54f",
    "BEARISH":             "#ff6d00",
    "AVOID":               "#ff1744",
}

SIGNAL_BG = {
    "HIGH CONVICTION BUY": "rgba(0,230,118,0.15)",
    "BULLISH":             "rgba(105,240,174,0.10)",
    "NEUTRAL":             "rgba(255,213,79,0.10)",
    "BEARISH":             "rgba(255,109,0,0.12)",
    "AVOID":               "rgba(255,23,68,0.12)",
}

SIG60_COLORS = {
    "STRUCTURAL BUY": "#00e5ff",
    "EXHAUSTED":      "#ff6d00",
    "AVOID":          "#546e7a",
}

REGIME_META = {
    "RISK_ON":  {"label": "RISK-ON",  "color": "#00e676", "bg": "rgba(0,230,118,0.12)"},
    "NEUTRAL":  {"label": "NEUTRAL",  "color": "#ffd54f", "bg": "rgba(255,213,79,0.12)"},
    "RISK_OFF": {"label": "RISK-OFF", "color": "#ff6d00", "bg": "rgba(255,109,0,0.12)"},
    "CRASH":    {"label": "CRASH",    "color": "#ff1744", "bg": "rgba(255,23,68,0.15)"},
}

def clean_signal(s):
    """Strip emojis/symbols to get canonical signal key."""
    if not s:
        return "NEUTRAL"
    s = str(s).upper().strip()
    s = s.replace("⚡ ", "").replace("🛡️ ", "").replace("⚡", "").replace("🛡️", "").strip()
    return s

def signal_color(s):
    key = clean_signal(s)
    for k, v in SIGNAL_COLORS.items():
        if k in key:
            return v
    return "#78909c"

def signal_bg(s):
    key = clean_signal(s)
    for k, v in SIGNAL_BG.items():
        if k in key:
            return v
    return "transparent"

def sig60_color(s):
    key = clean_signal(s)
    for k, v in SIG60_COLORS.items():
        if k in key:
            return v
    return "#546e7a"

def regime_meta(r):
    r = str(r).upper().strip() if r else "NEUTRAL"
    return REGIME_META.get(r, REGIME_META["NEUTRAL"])

def fmt_score(v, scale=100):
    """Normalize: f_score/gv_score/etc come in as 0-100; s_hybrid/s_structural as 0-1."""
    try:
        n = float(v)
        if scale == 100:
            return n / 100  # normalize to 0-1 for display
        return n
    except:
        return 0.0

def score_bar_html(value_01, color):
    pct = max(0, min(100, value_01 * 100))
    return f"""
    <div style="height:3px;background:rgba(255,255,255,0.05);border-radius:2px;margin-top:3px;">
      <div style="height:100%;width:{pct:.0f}%;background:{color};border-radius:2px;box-shadow:0 0 4px {color}66;"></div>
    </div>"""

def action_badge(action_str):
    a = str(action_str).upper() if action_str else ""
    if "ENTER" in a:
        return "#00e676", "rgba(0,230,118,0.12)"
    elif "ACCUMULATE" in a:
        return "#00e5ff", "rgba(0,229,255,0.10)"
    elif "EXIT" in a or "AVOID" in a:
        return "#ff1744", "rgba(255,23,68,0.12)"
    elif "LOCK" in a:
        return "#7c4dff", "rgba(124,77,255,0.12)"
    return "#78909c", "rgba(255,255,255,0.05)"


# ─────────────────────────────────────────────
# 4. DATA LAYER
# ─────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(
            host=creds["host"],
            port=creds["port"],
            database=creds["database"],
            user=creds["user"],
            password=creds["password"],
            sslmode="require"
        )
        df = pd.read_sql(
            "SELECT * FROM mpulse_execution_results ORDER BY tradedate DESC, rank ASC",
            conn
        )
        conn.close()
        df.columns = [c.lower() for c in df.columns]
        if "tradedate" in df.columns:
            df["tradedate"] = pd.to_datetime(df["tradedate"])
            df["date_str"] = df["tradedate"].dt.strftime("%Y-%m-%d")
        for col in ["f_score", "gv_score", "smart_money_score", "analyst_score",
                    "pipeline_score", "risk_score", "s_hybrid", "s_structural",
                    "sector_strength", "sector_weight", "final_weight", "kelly_fraction",
                    "target_pct", "vix", "spx", "spx_200dma", "beta", "vol_scale",
                    "w_vol", "w_kelly", "sector_penalty"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        st.error(f"⚠️ Database connection failed: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# 5. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:0 0 12px 0;border-bottom:1px solid #1e2d3d;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;background:linear-gradient(135deg,#00e676,#00acc1);border-radius:5px;display:flex;align-items:center;justify-content:center;">
          <span style="font-size:13px;font-weight:700;color:#080c10;font-family:'Barlow Condensed',sans-serif;">mP</span>
        </div>
        <div>
          <div style="font-size:14px;font-weight:700;color:#eceff1;font-family:'Barlow Condensed',sans-serif;letter-spacing:0.06em;">mPULSEINSIGHT</div>
          <div style="font-size:8px;color:#37474f;letter-spacing:0.14em;">ALPHA ENGINE v3.1</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🔍 Filters")
    ticker_search = st.text_input("Ticker / Sector", "", placeholder="e.g. NVDA, Technology").upper()

    st.markdown("#### 📅 Date Range")
    lookback_days = st.slider("Signal lookback (days)", 1, 60, 5)

    st.markdown("#### 🎯 Signal Filter")
    sig_filter = st.multiselect(
        "Show signals",
        ["HIGH CONVICTION BUY", "BULLISH", "NEUTRAL", "BEARISH"],
        default=["HIGH CONVICTION BUY", "BULLISH"],
        label_visibility="collapsed"
    )

    st.markdown("#### ⚙️ Display")
    show_audit = st.checkbox("Show audit columns", value=False)
    min_score = st.slider("Min S_hybrid score", 0.0, 1.0, 0.0, 0.05)

    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("""
    <div style="margin-top:20px;padding:10px;background:#0d1821;border:1px solid #1e2d3d;border-radius:4px;">
      <div style="font-size:8px;color:#37474f;letter-spacing:0.12em;margin-bottom:6px;">RISK CONTROLS</div>
      <div style="font-size:9px;color:#546e7a;line-height:1.8;">
        ✓ Half-Kelly sizing active<br>
        ✓ 20% vol cap enforced<br>
        ✓ Sector penalty applied<br>
        ✓ 5% max per position
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 6. LOAD DATA
# ─────────────────────────────────────────────
with st.spinner("Loading market intelligence..."):
    df = load_data()

if df.empty:
    st.warning("No data available. Check your database connection in `.streamlit/secrets.toml`.")
    st.stop()

# Compute recent dates window
all_dates = sorted(df["date_str"].dropna().unique(), reverse=True)
recent_dates = all_dates[:lookback_days]
latest_date  = all_dates[0] if all_dates else None

latest_snap = df[df["date_str"] == latest_date].sort_values("rank").iloc[0] if latest_date else df.iloc[0]


# ─────────────────────────────────────────────
# 7. TOP HEADER BAR
# ─────────────────────────────────────────────
rm = regime_meta(latest_snap.get("final_regime", "NEUTRAL"))
vix_val = latest_snap.get("vix", 0) or 0
spx_val = latest_snap.get("spx", 0) or 0
spx_200 = latest_snap.get("spx_200dma", 1) or 1
spx_ratio = (spx_val / spx_200 * 100) - 100 if spx_200 else 0

st.markdown(f"""
<div style="background:#0b1016;border:1px solid #1e2d3d;border-radius:6px;
            padding:14px 20px;margin-bottom:18px;
            display:flex;align-items:center;justify-content:space-between;">
  <div style="display:flex;align-items:center;gap:16px;">
    <span class="status-dot"></span>
    <span style="font-size:11px;color:#37474f;letter-spacing:0.1em;">LIVE INTELLIGENCE</span>
    <span style="font-size:11px;color:#546e7a;">AS AT {latest_date or 'N/A'}</span>
  </div>
  <div style="display:flex;align-items:center;gap:14px;">
    <div style="text-align:right;">
      <div style="font-size:10px;color:#37474f;letter-spacing:0.08em;">VIX</div>
      <div style="font-size:15px;font-family:'Barlow Condensed',sans-serif;font-weight:700;
                  color:{'#ff6d00' if vix_val>25 else '#ffd54f' if vix_val>20 else '#00e676'};">
        {vix_val:.2f}
      </div>
    </div>
    <div style="width:1px;height:28px;background:#1e2d3d;"></div>
    <div style="text-align:right;">
      <div style="font-size:10px;color:#37474f;letter-spacing:0.08em;">SPX vs 200DMA</div>
      <div style="font-size:15px;font-family:'Barlow Condensed',sans-serif;font-weight:700;
                  color:{'#00e676' if spx_ratio>=0 else '#ff6d00'};">
        {spx_ratio:+.1f}%
      </div>
    </div>
    <div style="width:1px;height:28px;background:#1e2d3d;"></div>
    <div style="padding:5px 14px;background:{rm['bg']};border:1px solid {rm['color']}44;border-radius:3px;">
      <span style="font-size:11px;color:{rm['color']};font-weight:700;letter-spacing:0.12em;">
        ⬡ {rm['label']}
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 8. PORTFOLIO KPI STRIP
# ─────────────────────────────────────────────
latest_df = df[df["date_str"] == latest_date] if latest_date else df.head(50)
total_assets   = latest_df["symbol"].nunique()
enter_count    = latest_df[latest_df["action"].str.upper().str.contains("ENTER", na=False)].shape[0]
accum_count    = latest_df[latest_df["action"].str.upper().str.contains("ACCUMULATE", na=False)].shape[0]
core_long      = latest_df[latest_df.get("execution_stance", pd.Series(dtype=str)).str.upper().str.contains("CORE_LONG", na=False)].shape[0] if "execution_stance" in latest_df.columns else 0
total_deployed = latest_df["final_dollars"].sum() if "final_dollars" in latest_df.columns else 0
avg_conf       = latest_df["kelly_fraction"].mean() * 100 if "kelly_fraction" in latest_df.columns else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Universe",       f"{total_assets}",            "S&P 500 signals")
k2.metric("ENTER signals",  f"{enter_count}",             f"+{accum_count} ACCUMULATE")
k3.metric("CORE LONG",      f"{core_long}",               "Daily + 60D aligned")
k4.metric("Deployed $",     f"${total_deployed:,.0f}",    "Today's allocation")
k5.metric("Avg Confidence", f"{avg_conf:.0f}%",           "Kelly-weighted")
k6.metric("Regime",         rm["label"],                  f"VIX {vix_val:.1f}")


# ─────────────────────────────────────────────
# 9. MAIN TABS
# ─────────────────────────────────────────────
tab_matrix, tab_exec, tab_sector, tab_backtest = st.tabs([
    "📡  SIGNAL MATRIX",
    "⚡  EXECUTION TABLE",
    "🏗️  SECTOR BREADTH",
    "📈  RESEARCH & HISTORY"
])


# ══════════════════════════════════════════════
# TAB 1 — SIGNAL MATRIX (pivot heatmap)
# ══════════════════════════════════════════════
with tab_matrix:
    st.markdown("### Signal Matrix — Rolling Window")

    matrix_df = df[df["date_str"].isin(recent_dates)].copy()
    if ticker_search:
        matrix_df = matrix_df[
            matrix_df["symbol"].str.contains(ticker_search, na=False) |
            matrix_df.get("sector", pd.Series(dtype=str)).str.contains(ticker_search, case=False, na=False)
        ]
    if sig_filter:
        def sig_match(s):
            cs = clean_signal(s)
            return any(f in cs for f in sig_filter)
        # Keep tickers that had ANY matching signal in the window
        matching_tickers = matrix_df[matrix_df["signal"].apply(sig_match)]["symbol"].unique()
        matrix_df = matrix_df[matrix_df["symbol"].isin(matching_tickers)]
    if min_score > 0:
        matrix_df = matrix_df[matrix_df["s_hybrid"] >= min_score]

    if matrix_df.empty:
        st.info("No signals match your filters.")
    else:
        # Build pivot
        pivot = matrix_df.pivot_table(
            index=["symbol", "sector"] if "sector" in matrix_df.columns else ["symbol"],
            columns="date_str",
            values="signal",
            aggfunc="first"
        ).reset_index()

        # Latest rank merge for ordering
        latest_ranks = matrix_df[matrix_df["date_str"] == latest_date][["symbol","rank","s_hybrid"]].drop_duplicates("symbol")
        pivot = pivot.merge(latest_ranks, on="symbol", how="left").sort_values("rank", na_position="last")

        st.caption(f"Showing {len(pivot)} assets · {len(recent_dates)} days · columns = date")

        # Styled display using st.dataframe with color map
        display_cols = [c for c in pivot.columns if c not in ["rank", "s_hybrid"]]
        display_df = pivot[display_cols].set_index("symbol")

        def color_signal_cell(val):
            cs = clean_signal(str(val))
            c = signal_color(cs)
            bg = signal_bg(cs)
            return f"color: {c}; background-color: {bg}; font-weight: 600; font-size: 11px; font-family: 'JetBrains Mono', monospace;"

        date_cols = [c for c in display_df.columns if c not in ["sector"]]
        styled = display_df.style.applymap(color_signal_cell, subset=date_cols)
        st.dataframe(styled, use_container_width=True, height=420)


# ══════════════════════════════════════════════
# TAB 2 — EXECUTION TABLE (full 15-col view)
# ══════════════════════════════════════════════
with tab_exec:
    st.markdown("### Execution Intelligence — Today's Orders")

    exec_df = df[df["date_str"] == latest_date].copy() if latest_date else df.head(100)

    # Apply filters
    if ticker_search:
        exec_df = exec_df[
            exec_df["symbol"].str.contains(ticker_search, na=False) |
            exec_df.get("sector", pd.Series(dtype=str)).str.contains(ticker_search, case=False, na=False)
        ]
    if sig_filter:
        exec_df = exec_df[exec_df["signal"].apply(lambda s: any(f in clean_signal(s) for f in sig_filter))]
    if min_score > 0:
        exec_df = exec_df[exec_df["s_hybrid"] >= min_score]

    # Define column sets
    core_cols = ["rank", "symbol", "sector", "s_hybrid", "signal", "action",
                 "target_pct", "final_dollars", "execution_stance",
                 "suggested_action", "signal_60d", "action_60d"]
    factor_cols = ["f_score", "gv_score", "smart_money_score", "analyst_score",
                   "pipeline_score", "risk_score"]
    audit_cols = ["beta", "vol_scale", "kelly_fraction", "w_kelly", "w_vol",
                  "sector_penalty", "s_sector", "sector_weight",
                  "w_final_pre_sector", "final_weight", "s_structural", "sector_strength"]

    show_cols = [c for c in core_cols + factor_cols + (audit_cols if show_audit else [])
                 if c in exec_df.columns]
    table_data = exec_df[show_cols].copy()

    # Normalize factor scores for display
    for fc in factor_cols:
        if fc in table_data.columns:
            table_data[fc] = (table_data[fc] / 100).round(3)

    # Summary metrics above table
    e1, e2, e3, e4, e5 = st.columns(5)
    enter_rows = exec_df[exec_df["action"].str.upper().str.contains("ENTER", na=False)]
    e1.metric("ENTER", f"{len(enter_rows)}", "positions today")
    accum_rows = exec_df[exec_df["action"].str.upper().str.contains("ACCUMULATE", na=False)]
    e2.metric("ACCUMULATE", f"{len(accum_rows)}", "add to position")
    cl_rows = exec_df[exec_df.get("execution_stance", pd.Series(dtype=str)).str.upper().str.contains("CORE", na=False)] if "execution_stance" in exec_df.columns else pd.DataFrame()
    e3.metric("CORE LONG", f"{len(cl_rows)}", "daily + 60D aligned")
    total_buy = exec_df[exec_df["final_dollars"] > 0]["final_dollars"].sum() if "final_dollars" in exec_df.columns else 0
    e4.metric("Total Buy $", f"${total_buy:,.0f}", "allocated today")
    avg_shybrid = exec_df["s_hybrid"].mean() if "s_hybrid" in exec_df.columns else 0
    e5.metric("Avg S_hybrid", f"{avg_shybrid:.3f}", "portfolio quality")

    st.markdown("---")

    # Render with styling
    def style_exec_table(df_in):
        def row_style(row):
            styles = [""] * len(row)
            return styles

        def col_signal(val):
            cs = clean_signal(str(val))
            return f"color:{signal_color(cs)};background:{signal_bg(cs)};font-weight:700;font-size:10px;"

        def col_action(val):
            c, bg = action_badge(str(val))
            return f"color:{c};background:{bg};font-weight:700;font-size:10px;"

        def col_hybrid(val):
            try:
                v = float(val)
                c = "#00e676" if v >= 0.75 else "#ffd54f" if v >= 0.55 else "#ff6d00"
                return f"color:{c};font-weight:700;"
            except:
                return ""

        def col_dollars(val):
            try:
                return f"color:{'#00e676' if float(val) > 0 else '#37474f'};font-weight:600;"
            except:
                return ""

        styled = df_in.style
        if "signal" in df_in.columns:
            styled = styled.applymap(col_signal, subset=["signal"])
        if "action" in df_in.columns:
            styled = styled.applymap(col_action, subset=["action"])
        if "s_hybrid" in df_in.columns:
            styled = styled.applymap(col_hybrid, subset=["s_hybrid"])
        if "final_dollars" in df_in.columns:
            styled = styled.applymap(col_dollars, subset=["final_dollars"])
        if "signal_60d" in df_in.columns:
            styled = styled.applymap(
                lambda v: f"color:{sig60_color(v)};font-size:10px;",
                subset=["signal_60d"]
            )
        if "suggested_action" in df_in.columns:
            styled = styled.applymap(
                lambda v: "color:#00e676;font-weight:600;" if "BUY" in str(v).upper() else "color:#37474f;",
                subset=["suggested_action"]
            )
        return styled

    styled_table = style_exec_table(table_data)
    st.dataframe(styled_table, use_container_width=True, height=500)

    # ── Asset Intelligence Panel (select ticker for drill-down) ──
    st.markdown("---")
    st.markdown("### 🔍 Asset Intelligence Drill-Down")

    all_tickers = sorted(exec_df["symbol"].dropna().unique().tolist())
    if all_tickers:
        col_sel, col_void = st.columns([2, 3])
        with col_sel:
            selected_ticker = st.selectbox("Select asset for deep analysis", all_tickers,
                                            index=0, label_visibility="collapsed")

        if selected_ticker:
            ticker_hist = df[df["symbol"] == selected_ticker].sort_values("tradedate", ascending=False)
            latest_row  = ticker_hist.iloc[0] if not ticker_hist.empty else None

            if latest_row is not None:
                sig_clean   = clean_signal(latest_row.get("signal", ""))
                sig_color   = signal_color(sig_clean)
                sig_bg      = signal_bg(sig_clean)
                sig60_clean = clean_signal(latest_row.get("signal_60d", ""))
                rm_asset    = regime_meta(latest_row.get("final_regime", "NEUTRAL"))
                sugg_action = latest_row.get("suggested_action", "STAY CASH")
                exec_stance = latest_row.get("execution_stance", "TACTICAL")
                conf_pct    = int(latest_row.get("kelly_fraction", 0) * 100)

                # ── Header row ──
                h1, h2, h3, h4 = st.columns([2,2,2,2])

                with h1:
                    st.markdown(f"""
                    <div class="intel-card">
                      <div style="font-size:28px;font-family:'Barlow Condensed',sans-serif;
                                  font-weight:700;color:#eceff1;letter-spacing:0.04em;">{selected_ticker}</div>
                      <div style="font-size:9px;color:#37474f;margin-top:2px;">
                        {latest_row.get('sector','N/A')} · Rank #{int(latest_row.get('rank',0)) if pd.notna(latest_row.get('rank')) else 'N/A'}
                      </div>
                      <div style="margin-top:10px;padding:6px 10px;background:{sig_bg};
                                  border:1px solid {sig_color}44;border-radius:3px;">
                        <span style="font-size:12px;color:{sig_color};font-weight:700;
                                     letter-spacing:0.08em;">{latest_row.get('signal','N/A')}</span>
                      </div>
                      <div style="margin-top:6px;font-size:11px;color:#546e7a;">
                        60D: <span style="color:{sig60_color(sig60_clean)};font-weight:600;">
                          {latest_row.get('signal_60d','N/A')}
                        </span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                with h2:
                    s_hyb = float(latest_row.get("s_hybrid", 0) or 0)
                    s_str = float(latest_row.get("s_structural", 0) or 0)
                    c_hyb = "#00e676" if s_hyb >= 0.75 else "#ffd54f" if s_hyb >= 0.55 else "#ff6d00"
                    c_str = "#00e5ff" if s_str >= 0.70 else "#ffd54f" if s_str >= 0.55 else "#ff6d00"
                    st.markdown(f"""
                    <div class="intel-card">
                      <div style="font-size:8px;color:#37474f;letter-spacing:0.12em;margin-bottom:8px;">COMPOSITE SCORES</div>
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <span style="font-size:9px;color:#546e7a;">S_HYBRID (daily)</span>
                        <span style="font-size:20px;font-family:'Barlow Condensed';font-weight:700;color:{c_hyb};">{s_hyb:.3f}</span>
                      </div>
                      {score_bar_html(s_hyb, c_hyb)}
                      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;margin-bottom:4px;">
                        <span style="font-size:9px;color:#546e7a;">S_STRUCTURAL (60D)</span>
                        <span style="font-size:20px;font-family:'Barlow Condensed';font-weight:700;color:{c_str};">{s_str:.3f}</span>
                      </div>
                      {score_bar_html(s_str, c_str)}
                      <div style="margin-top:10px;font-size:9px;color:#37474f;">
                        Confidence: <span style="color:#eceff1;font-weight:700;">{conf_pct}%</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                with h3:
                    fdollars = int(latest_row.get("final_dollars", 0) or 0)
                    f_weight = float(latest_row.get("final_weight", 0) or 0)
                    ac, ab = action_badge(latest_row.get("action", "WAIT"))
                    st.markdown(f"""
                    <div class="intel-card">
                      <div style="font-size:8px;color:#37474f;letter-spacing:0.12em;margin-bottom:8px;">EXECUTION</div>
                      <div style="font-size:20px;font-family:'Barlow Condensed';font-weight:700;
                                  color:{'#00e676' if fdollars > 0 else '#546e7a'};">
                        {'$'+f"{fdollars:,}" if fdollars > 0 else 'STAY CASH'}
                      </div>
                      <div style="font-size:9px;color:#546e7a;margin:4px 0;">{sugg_action}</div>
                      <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
                        <span style="font-size:9px;padding:2px 7px;background:{ab};color:{ac};
                                     border-radius:2px;font-weight:700;letter-spacing:0.06em;">
                          {latest_row.get('action','WAIT')}
                        </span>
                        <span style="font-size:9px;padding:2px 7px;background:rgba(255,255,255,0.05);
                                     color:#78909c;border-radius:2px;letter-spacing:0.05em;">
                          {exec_stance}
                        </span>
                      </div>
                      <div style="margin-top:8px;font-size:9px;color:#37474f;">
                        Weight: <span style="color:#eceff1;">{f_weight*100:.2f}%</span> · 
                        60D: <span style="color:{sig60_color(sig60_clean)};">{latest_row.get('action_60d','N/A')}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                with h4:
                    beta_v = float(latest_row.get("beta", 1) or 1)
                    risk_v = float(latest_row.get("risk_score", 0.5) or 0.5)
                    sec_pen = float(latest_row.get("sector_penalty", 1) or 1)
                    sec_str = float(latest_row.get("sector_strength", 0) or 0)
                    rc = "#00e676" if risk_v < 0.30 else "#ffd54f" if risk_v < 0.50 else "#ff6d00"
                    st.markdown(f"""
                    <div class="intel-card">
                      <div style="font-size:8px;color:#37474f;letter-spacing:0.12em;margin-bottom:8px;">RISK PROFILE</div>
                      <div class="factor-row">
                        <span class="factor-label">RISK SCORE</span>
                        <span style="font-size:13px;font-weight:700;color:{rc};">{risk_v:.3f}</span>
                      </div>
                      <div class="factor-row">
                        <span class="factor-label">BETA</span>
                        <span style="font-size:13px;font-weight:700;color:#eceff1;">{beta_v:.2f}x</span>
                      </div>
                      <div class="factor-row">
                        <span class="factor-label">SECTOR PENALTY</span>
                        <span style="font-size:13px;font-weight:700;color:{'#00e676' if sec_pen==1.0 else '#ff6d00'};">
                          {sec_pen:.1f}x
                        </span>
                      </div>
                      <div class="factor-row">
                        <span class="factor-label">SECTOR BREADTH</span>
                        <span style="font-size:13px;font-weight:700;color:{'#00e676' if sec_str>=0.30 else '#ff6d00'};">
                          {sec_str*100:.0f}%
                        </span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                # ── Factor score breakdown ──
                st.markdown("#### Factor Score Breakdown")
                FACTORS = [
                    ("Fundamentals (F)",     "f_score",           "22–30%", "Revenue CAGR, EPS, ROE, FCF, Piotroski"),
                    ("Growth Valuation (gV)","gv_score",          "18–32%", "PEG, ROIC persistence, FCF yield"),
                    ("Smart Money (Ṡ)",      "smart_money_score", "8–22%",  "Insider buying, institutional Δ, buyback yield"),
                    ("Analyst Consensus (Ã)","analyst_score",     "10–22%", "Price target ratio, buy ratio"),
                    ("Pipeline (P)",         "pipeline_score",    "14–26%", "R&D intensity, patent momentum"),
                    ("Risk Control (r)",     "risk_score",        "20–30%", "β, MaxDD, downside beta — LOWER = better"),
                ]
                f_cols = st.columns(3)
                for idx, (fname, fkey, fweight, fdesc) in enumerate(FACTORS):
                    raw_val = float(latest_row.get(fkey, 0) or 0)
                    # risk_score is already 0-1; others are 0-100
                    if fkey == "risk_score":
                        norm_val = raw_val
                        disp_val = raw_val
                        is_risk  = True
                    else:
                        norm_val = raw_val / 100
                        disp_val = raw_val
                        is_risk  = False

                    if is_risk:
                        c = "#00e676" if norm_val < 0.30 else "#ffd54f" if norm_val < 0.50 else "#ff6d00"
                        bar_val = 1 - norm_val  # invert for visual (lower risk = more green)
                    else:
                        c = "#00e676" if norm_val >= 0.75 else "#ffd54f" if norm_val >= 0.55 else "#ff6d00"
                        bar_val = norm_val

                    with f_cols[idx % 3]:
                        st.markdown(f"""
                        <div style="background:#0d1821;border:1px solid #1e2d3d;border-radius:4px;
                                    padding:10px 12px;margin-bottom:8px;">
                          <div style="font-size:9px;color:#546e7a;font-weight:600;letter-spacing:0.08em;
                                      margin-bottom:2px;">{fname}</div>
                          <div style="font-size:8px;color:#37474f;margin-bottom:6px;">{fdesc}</div>
                          <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:8px;color:#37474f;">weight {fweight}</span>
                            <span style="font-size:16px;font-family:'Barlow Condensed';font-weight:700;color:{c};">
                              {disp_val:.1f}{'(risk)' if is_risk else ''}
                            </span>
                          </div>
                          {score_bar_html(bar_val, c)}
                        </div>
                        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 3 — SECTOR BREADTH
# ══════════════════════════════════════════════
with tab_sector:
    st.markdown("### Sector Breadth Analysis")

    if "sector" not in df.columns:
        st.info("No sector data available.")
    else:
        sec_df = df[df["date_str"] == latest_date].copy() if latest_date else df.copy()

        def classify(sig):
            cs = clean_signal(sig)
            if "HIGH CONVICTION" in cs or "BULLISH" in cs:
                return "Bullish"
            elif "BEARISH" in cs:
                return "Bearish"
            else:
                return "Neutral"

        sec_df["sig_class"] = sec_df["signal"].apply(classify)

        sector_stats = sec_df.groupby("sector").agg(
            total   = ("symbol", "count"),
            bullish = ("sig_class", lambda x: (x == "Bullish").sum()),
            bearish = ("sig_class", lambda x: (x == "Bearish").sum()),
            avg_hybrid = ("s_hybrid", "mean"),
            total_dollars = ("final_dollars", "sum"),
        ).reset_index()
        sector_stats["bull_pct"] = (sector_stats["bullish"] / sector_stats["total"] * 100).round(1)
        sector_stats["breadth"]  = (sector_stats["bullish"] / sector_stats["total"]).round(3)
        sector_stats = sector_stats.sort_values("bull_pct", ascending=False)

        # ── Breadth bar chart ──
        fig_breadth = go.Figure()
        colors = ["#00e676" if v >= 50 else "#ffd54f" if v >= 30 else "#ff6d00"
                  for v in sector_stats["bull_pct"]]
        fig_breadth.add_trace(go.Bar(
            x=sector_stats["sector"],
            y=sector_stats["bull_pct"],
            marker_color=colors,
            text=[f"{v:.0f}%" for v in sector_stats["bull_pct"]],
            textposition="outside",
            textfont=dict(size=10, color="#90a4ae"),
        ))
        fig_breadth.update_layout(
            title="Bullish % by Sector",
            template="plotly_dark",
            paper_bgcolor="#080c10",
            plot_bgcolor="#0b1016",
            font=dict(family="JetBrains Mono", color="#78909c", size=10),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(gridcolor="#1e2d3d"),
            yaxis=dict(gridcolor="#1e2d3d", range=[0, 110]),
            showlegend=False,
        )
        st.plotly_chart(fig_breadth, use_container_width=True)

        # ── Sector table ──
        display_sec = sector_stats[[
            "sector", "total", "bullish", "bearish", "bull_pct", "avg_hybrid", "total_dollars"
        ]].rename(columns={
            "sector": "Sector", "total": "# Assets", "bullish": "Bullish",
            "bearish": "Bearish", "bull_pct": "Bull%", "avg_hybrid": "Avg S_hybrid",
            "total_dollars": "Allocated $"
        })

        def style_sector(v):
            if isinstance(v, float) and v >= 50:
                return "color:#00e676;font-weight:700;"
            elif isinstance(v, float) and v >= 30:
                return "color:#ffd54f;"
            elif isinstance(v, float) and v < 30:
                return "color:#ff6d00;"
            return ""

        st.dataframe(
            display_sec.style.applymap(style_sector, subset=["Bull%"]),
            use_container_width=True, hide_index=True
        )

        # ── Sector penalty warning ──
        penalized = sec_df[sec_df.get("sector_penalty", pd.Series(dtype=float)) < 1.0] if "sector_penalty" in sec_df.columns else pd.DataFrame()
        if not penalized.empty:
            penalized_sectors = penalized["sector"].unique()
            st.warning(f"⚠️ Sector penalty active on: **{', '.join(penalized_sectors)}** — breadth < 30% threshold")


# ══════════════════════════════════════════════
# TAB 4 — RESEARCH & HISTORY
# ══════════════════════════════════════════════
with tab_backtest:
    st.markdown("### Research & Signal History")

    all_tickers_bt = sorted(df["symbol"].dropna().unique().tolist())
    bt_col1, bt_col2 = st.columns([2, 4])

    with bt_col1:
        bt_ticker = st.selectbox("Select ticker", all_tickers_bt,
                                  index=0 if all_tickers_bt else 0)
        bt_days   = st.slider("History (days)", 5, 90, 30, key="bt_days")

    hist = df[df["symbol"] == bt_ticker].sort_values("tradedate").tail(bt_days) if bt_ticker else pd.DataFrame()

    if hist.empty:
        st.info("No history for selected ticker.")
    else:
        # ── S_hybrid trend chart ──
        fig = go.Figure()

        # Background regime shading
        regimes = hist["final_regime"].fillna("NEUTRAL")
        regime_colors_map = {"RISK_ON": "rgba(0,230,118,0.04)", "NEUTRAL": "rgba(255,213,79,0.04)",
                             "RISK_OFF": "rgba(255,109,0,0.06)", "CRASH": "rgba(255,23,68,0.08)"}

        fig.add_trace(go.Scatter(
            x=hist["tradedate"], y=hist["s_hybrid"],
            name="S_hybrid (daily)",
            line=dict(color="#00e676", width=2.5),
            fill="tozeroy", fillcolor="rgba(0,230,118,0.06)"
        ))
        if "s_structural" in hist.columns:
            fig.add_trace(go.Scatter(
                x=hist["tradedate"], y=hist["s_structural"],
                name="S_structural (60D)",
                line=dict(color="#00e5ff", width=2, dash="dot"),
            ))

        # Threshold lines
        fig.add_hline(y=0.78, line=dict(color="#00e676", dash="dash", width=1),
                      annotation_text="HIGH CONVICTION", annotation_font_size=9)
        fig.add_hline(y=0.60, line=dict(color="#ffd54f", dash="dash", width=1),
                      annotation_text="BULLISH", annotation_font_size=9)
        fig.add_hline(y=0.45, line=dict(color="#ff6d00", dash="dash", width=1),
                      annotation_text="BEARISH", annotation_font_size=9)

        fig.update_layout(
            title=f"{bt_ticker} — Composite Score History ({bt_days}d)",
            template="plotly_dark",
            paper_bgcolor="#080c10",
            plot_bgcolor="#0b1016",
            font=dict(family="JetBrains Mono", color="#78909c", size=10),
            height=320,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(gridcolor="#1e2d3d"),
            yaxis=dict(gridcolor="#1e2d3d", range=[0, 1.05]),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Factor history sparklines ──
        factor_keys = [("f_score","F"), ("gv_score","gV"), ("smart_money_score","Ṡ"),
                       ("analyst_score","Ã"), ("pipeline_score","P"), ("risk_score","r")]
        available_factors = [(k, label) for k, label in factor_keys if k in hist.columns]

        if available_factors:
            fig2 = go.Figure()
            FACTOR_COLORS = ["#00e676","#00e5ff","#ffd54f","#7c4dff","#ff6d00","#ef9a9a"]
            for i, (fk, fl) in enumerate(available_factors):
                vals = hist[fk].copy()
                # normalize to 0-1
                if fk != "risk_score":
                    vals = vals / 100
                fig2.add_trace(go.Scatter(
                    x=hist["tradedate"], y=vals,
                    name=fl,
                    line=dict(color=FACTOR_COLORS[i % len(FACTOR_COLORS)], width=1.5),
                ))

            fig2.update_layout(
                title="Factor Score Trends (normalized 0–1)",
                template="plotly_dark",
                paper_bgcolor="#080c10",
                plot_bgcolor="#0b1016",
                font=dict(family="JetBrains Mono", color="#78909c", size=10),
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(gridcolor="#1e2d3d"),
                yaxis=dict(gridcolor="#1e2d3d", range=[0, 1.05]),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9), orientation="h"),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Signal log table ──
        st.markdown("#### Signal Log")
        log_cols = ["date_str","rank","signal","signal_60d","action","action_60d",
                    "s_hybrid","s_structural","suggested_action","execution_stance","notes"]
        log_cols = [c for c in log_cols if c in hist.columns]
        log_df = hist[log_cols].sort_values("date_str", ascending=False)

        st.dataframe(
            log_df.style.applymap(
                lambda v: f"color:{signal_color(v)};font-weight:600;font-size:10px;",
                subset=[c for c in ["signal","signal_60d"] if c in log_df.columns]
            ).applymap(
                lambda v: f"color:{action_badge(v)[0]};font-size:10px;",
                subset=[c for c in ["action","action_60d"] if c in log_df.columns]
            ),
            use_container_width=True, hide_index=True, height=320
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:8px 4px;font-size:9px;color:#1e2d3d;letter-spacing:0.1em;">
  <span>mPulseInsight™ v3.1 · 6-Factor Orthogonal Alpha System · Regime-Adaptive Execution</span>
  <span>⚡ HALF-KELLY ✓  &nbsp;·&nbsp; 20% VOL CAP ✓  &nbsp;·&nbsp; SECTOR PENALTY ✓  &nbsp;·&nbsp; TIERED EXITS ✓</span>
</div>
""", unsafe_allow_html=True)
