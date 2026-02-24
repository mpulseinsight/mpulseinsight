import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Intelligence", layout="wide", initial_sidebar_state="expanded")

# 2. Advanced Professional CSS
st.markdown("""
    <style>
        /* Main background and font */
        .stApp { background-color: #F8F9FA; }
        
        /* Metric Card Styling */
        div[data-testid="stMetric"] {
            background-color: white;
            border: 1px solid #E0E0E0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Grouping Logic Containers */
        .logic-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #1A73E8;
            margin-bottom: 20px;
        }
        
        /* Remove extra padding */
        .block-container { padding-top: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# 3. Comprehensive Data Dictionary (The "Meaning" Map)
FIELD_GROUPS = {
    "🎯 Core Strategy": {
        "execution_stance": "Strategy Type",
        "suggested_action": "Current Instruction",
        "signal": "Daily Bias",
        "signal_60d": "60D Horizon",
        "target_pct": "Optimal Target %"
    },
    "📊 Momentum & Trend": {
        "s_hybrid": "Pulse Score",
        "s_structural": "Structural Health",
        "s_sector": "Sector Score",
        "trend_regime": "Trend State"
    },
    "🛡️ Risk & Allocation": {
        "final_weight": "Portfolio Weight",
        "final_dollars": "Dollar Size",
        "kelly_fraction": "Kelly Confidence",
        "vol_scale": "Vol Adjuster",
        "beta": "Sensitivity (Beta)",
        "risk_score": "Internal Risk Score"
    },
    "🏢 Fundamental & Sentiment": {
        "f_score": "Financial Health",
        "gv_score": "Growth/Value Ratio",
        "smart_money_score": "Institutional Accum.",
        "analyst_score": "Wall Street Rating"
    }
}

# 4. Popups
@st.dialog("Complete Technical Audit", width="large")
def show_full_audit(ticker, raw_data):
    st.subheader(f"Full Data Audit: {ticker}")
    d = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    
    # Render fields in meaningful groups
    cols = st.columns(2)
    for i, (group_name, fields) in enumerate(FIELD_GROUPS.items()):
        with cols[i % 2]:
            st.markdown(f"#### {group_name}")
            for key, label in fields.items():
                val = d.get(key, "N/A")
                # Formatting
                if isinstance(val, float): val = f"{val:.4f}"
                if "weight" in key or "pct" in key: val = f"{float(val)*100:.2f}%" if val != "N/A" else "N/A"
                
                st.write(f"**{label}**: `{val}`")
            st.markdown("---")

# 5. Data Engine
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate ASC", conn)
        conn.close()
        
        df['date_str'] = df['tradedate'].astype(str)
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

# 6. UI Structure
raw_df = load_data()

with st.sidebar:
    st.title("Settings")
    view_daily = st.checkbox("Show Daily Signal", value=True)
    view_60d = st.checkbox("Show 60D Signal", value=True)
    st.markdown("---")
    st.markdown("### 🔍 Perspective Help")
    st.caption("Daily: Focused on 1-5 day swings.\n60D: Focused on multi-week structure.")

# Top KPI Ribbon
if not raw_df.empty:
    latest_market = raw_df.iloc[-1]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Regime", latest_market['final_regime'])
    k2.metric("VIX Level", f"{latest_market['vix']:.2f}")
    k3.metric("SPX Trend", latest_market['trend_regime'])
    k4.metric("Active Coverage", len(raw_df['symbol'].unique()))

# 7. Main Matrix
st.markdown("### Market Intelligence Matrix")

# Prepare Pivot
def fmt_cell(row):
    p = []
    if view_daily: p.append(row['signal'])
    if view_60d: p.append(f"🛡️ {row['signal_60d']}")
    return " | ".join(p)

raw_df['cell_val'] = raw_df.apply(fmt_cell, axis=1)
recent_dates = sorted(raw_df['date_str'].unique().tolist(), reverse=True)[:5]
pivot = raw_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='cell_val', aggfunc='first').reset_index()

gb = GridOptionsBuilder.from_dataframe(pivot)
gb.configure_default_column(resizable=True, filterable=True, sortable=True)
gb.configure_column("symbol", pinned="left", header_name="Ticker", width=100)
gb.configure_column("sector", header_name="Industry", width=140)

# Make Date Columns Expandable and Clear
js_style = JsCode("""
function(params) {
    if (!params.value) return {};
    const v = params.value.toUpperCase();
    if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
    if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
    return {color: '#5F6368'};
}
""")

for d_col in recent_dates:
    gb.configure_column(d_col, width=220, cellStyle=js_style) # Fixed width for visibility

gb.configure_selection(selection_mode="single")
grid_out = AgGrid(pivot, gridOptions=gb.build(), allow_unsafe_jscode=True, height=450, theme="alpine")

# 8. Intelligence Panel
st.markdown("---")
sel = grid_out.get('selected_rows')
if sel is not None and len(sel) > 0:
    row = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
    ticker = row['symbol']
    d = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]

    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown(f"## {ticker}")
        st.markdown(f"**Industry:** {d['sector']}")
        st.button("🔬 Open Full Technical Audit", on_click=show_full_audit, args=(ticker, raw_df))
        
        st.markdown(f"""
            <div class="logic-card">
                <p style="margin:0; font-size:12px; color:#5F6368;">RECOMMENDED ACTION</p>
                <h3 style="margin:0; color:#1A73E8;">{d['suggested_action']}</h3>
                <p style="margin:0; font-weight:bold;">{d['execution_stance']}</p>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("### Confidence Matrix")
        f1, f2, f3 = st.columns(3)
        # Showing nested fields in logical spots
        f1.metric("Pulse Score", f"{d['s_hybrid']:.2f}")
        f2.metric("Structure", f"{d['s_structural']:.2f}")
        f3.metric("Final Weight", f"{d['final_weight']*100:.2f}%")
        
        # Progress bars for a "Health Check" feel
        st.progress(float(d['smart_money_score']), text=f"Institutional Accumulation: {d['smart_money_score']:.2f}")
        st.progress(float(d['f_score']), text=f"Financial Health: {d['f_score']:.2f}")
        st.progress(float(d['sector_strength']), text=f"Sector Breadth: {d['sector_strength']:.2f}")
else:
    st.info("Select a ticker from the matrix to view the deep intelligence profile.")
