import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. THE MASTER METADATA DICTIONARY (Fixed & Centralized)
# This explains every SQL field and the signal logic
METADATA = {
    "Execution Signals": {
        "signal": "Daily Pulse: Short-term momentum direction (Bullish/Bearish).",
        "signal_60d": "Structural Horizon: 60-day trend strength and safety.",
        "execution_stance": "Strategic Stance: The final decision (CORE_LONG, TACTICAL, etc).",
        "suggested_action": "Tactical Instruction: Specific trade move (Buy, Trim, etc)."
    },
    "Math & Logic Fields": {
        "s_hybrid": "Pulse Score (0-1): Higher means stronger immediate momentum.",
        "s_structural": "Structural Score (0-1): Higher means better long-term trend.",
        "f_score": "Financial Health: Company's balance sheet strength.",
        "smart_money_score": "Institutional Flow: Are big banks buying?",
        "kelly_fraction": "Confidence Level: The statistical 'bet size' multiplier.",
        "final_weight": "Portfolio Allocation: The actual % of your book to invest."
    },
    "Market Environment": {
        "vix_regime": "Fear Level: High/Low volatility state.",
        "trend_regime": "Market Direction: Overall S&P 500 health.",
        "final_regime": "Unified Regime: The final 'weather' condition for trading."
    }
}

# 3. CSS for Readable Upper Buckets (Metrics)
st.markdown("""
    <style>
        /* Make Metric Labels Bold and Large */
        [data-testid="stMetricLabel"] { 
            font-size: 16px !important; 
            font-weight: 700 !important; 
            color: #5F6368 !important; 
        }
        /* Make Metric Values POP */
        [data-testid="stMetricValue"] { 
            font-size: 28px !important; 
            color: #1A73E8 !important; 
        }
        /* Metric Card Container */
        [data-testid="metric-container"] {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
        }
    </style>
""", unsafe_allow_html=True)

# 4. Master Technical Audit & Dictionary Window
@st.dialog("Metadata & Technical Audit", width="large")
def show_tech_audit(ticker, raw_data):
    st.title(f"🔍 Deep Audit: {ticker}")
    d = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    
    # Toggle between Data Values and Definitions
    tab1, tab2 = st.tabs(["📊 Current Values", "📖 Field Dictionary"])
    
    with tab1:
        st.markdown("#### Live SQL Field Values")
        cols = st.columns(3)
        # Iterate through all fields in the DB row
        all_fields = list(d.index)
        for i, field in enumerate(all_fields):
            with cols[i % 3]:
                val = d[field]
                # Readable formatting
                if isinstance(val, float): val = round(val, 4)
                st.markdown(f"**{field}**")
                st.code(val)

    with tab2:
        st.markdown("#### What do these fields mean?")
        for category, items in METADATA.items():
            with st.expander(category, expanded=True):
                for field, definition in items.items():
                    st.write(f"**{field}**: {definition}")

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
        st.error(f"Error: {e}")
        return pd.DataFrame()

raw_df = load_data()

# 6. Upper Buckets (The KPI Ribbon)
if not raw_df.empty:
    latest = raw_df.iloc[-1]
    # Spaced out for readability
    st.markdown("### Market Context")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current Regime", latest['final_regime'])
    k2.metric("Market Fear (VIX)", f"{latest['vix']:.2f}")
    k3.metric("Trend State", latest['trend_regime'])
    k4.metric("Risk Level", "SAFE" if latest['vix'] < 20 else "CAUTION")

# 7. Main Grid Logic
st.markdown("---")
st.markdown("### Matrix: Daily & 60-Day Intelligence")

with st.sidebar:
    st.header("Perspective")
    view_daily = st.checkbox("Daily Signal", value=True)
    view_60d = st.checkbox("60-Day Signal", value=True)

# Prepare combined display for Grid
def combine_sig(row):
    bits = []
    if view_daily: bits.append(str(row['signal']))
    if view_60d: bits.append(f"🛡️ {row['signal_60d']}")
    return " | ".join(bits) if bits else "---"

raw_df['grid_display'] = raw_df.apply(combine_sig, axis=1)
recent_dates = sorted(raw_df['date_str'].unique().tolist(), reverse=True)[:5]
pivot = raw_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='grid_display', aggfunc='first').reset_index()

# Grid Builder
gb = GridOptionsBuilder.from_dataframe(pivot)
gb.configure_column("symbol", pinned="left", header_name="Ticker", width=100)
gb.configure_column("sector", header_name="Industry", width=140)

js_style = JsCode("""
function(params) {
    if (!params.value) return {};
    const v = params.value.toUpperCase();
    if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: '900'};
    if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: '900'};
    return {color: '#5F6368'};
}
""")

for d_col in recent_dates:
    gb.configure_column(d_col, width=220, cellStyle=js_style)

gb.configure_selection(selection_mode="single")
grid_out = AgGrid(pivot, gridOptions=gb.build(), allow_unsafe_jscode=True, height=450, theme="alpine")

# 8. Lower Intel Panel
sel = grid_out.get('selected_rows')
if sel is not None and len(sel) > 0:
    row = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
    ticker = row['symbol']
    d = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]

    st.markdown("---")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.header(ticker)
        st.write(f"**Strategy:** {d['execution_stance']}")
        st.button("🔬 Audit All Fields & Dictionary", on_click=show_tech_audit, args=(ticker, raw_df))
    
    with c2:
        st.info(f"**Instruction:** {d['suggested_action']}")
        st.progress(float(d['s_hybrid']), text=f"Daily Momentum: {d['s_hybrid']:.2f}")
        st.progress(float(d.get('s_structural', 0)), text=f"60D Structure: {d.get('s_structural', 0):.2f}")
