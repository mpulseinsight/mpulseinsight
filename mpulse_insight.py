import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Google Classic High-Contrast CSS
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; background-color: #FFFFFF; color: #202124; }
        header { visibility: hidden; }
        [data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #DADCE0; width: 350px !important; }
        
        /* High-Contrast Card Containers */
        div[data-testid="column"] { 
            background-color: #FFFFFF; border: 1px solid #BDC1C6; 
            padding: 15px; border-radius: 4px; margin-bottom: 10px;
        }
        
        /* Text Visibility Fixes */
        p, span, label, h1, h2, h3 { color: #202124 !important; font-family: 'Roboto', Arial, sans-serif; }
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; font-size: 12px !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; font-size: 24px !important; }

        /* Dictionary Table Styling */
        .dict-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .dict-table td, .dict-table th { border: 1px solid #DADCE0; padding: 6px; text-align: left; }
        .dict-table th { background-color: #F1F3F4; color: #5F6368; }

        /* Intelligence Grid Styling */
        .grid-header { background-color: #F1F3F4; padding: 6px 10px; font-weight: 700; color: #202124; border: 1px solid #DADCE0; }
        .grid-row { display: flex; justify-content: space-between; padding: 8px 12px; border: 1px solid #DADCE0; border-top: none; background: white; }
        .grid-label { color: #5F6368; font-weight: 500; }
        .grid-value { color: #1A73E8; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary Table
with st.sidebar:
    st.subheader("📖 Field Dictionary")
    st.markdown("""
    <table class="dict-table">
        <tr><th>Field</th><th>Meaning</th><th>Range & Icon</th></tr>
        <tr><td><b>Market Fear</b></td><td>VIX Panic Index</td><td>📉 10 - 80</td></tr>
        <tr><td><b>Regime</b></td><td>Market Trend Mode</td><td>🔄 ON / OFF</td></tr>
        <tr><td><b>Conviction</b></td><td>Master Score</td><td>🎯 0.0 - 1.0</td></tr>
        <tr><td><b>Safety Buffer</b></td><td>Volatility Resistance</td><td>🛡️ 0.0 - 1.0</td></tr>
        <tr><td><b>Strength</b></td><td>Fundamental Quality</td><td>💎 0.0 - 1.0</td></tr>
        <tr><td><b>Port. Share</b></td><td>Capital Allocation</td><td>💰 0% - 100%</td></tr>
        <tr><td><b>Cash Req.</b></td><td>Trade Dollar Amount</td><td>💵 $ Value</td></tr>
        <tr><td><b>GV Mix</b></td><td>Growth vs Value</td><td>⚖️ 0.0 - 1.0</td></tr>
        <tr><td><b>Pipeline</b></td><td>Catalyst Quality</td><td>🚀 0.0 - 1.0</td></tr>
        <tr><td><b>Smart Money</b></td><td>Institutional Flow</td><td>🏛️ 0.0 - 1.0</td></tr>
        <tr><td><b>Consensus</b></td><td>Analyst Ratings</td><td>📢 0.0 - 1.0</td></tr>
        <tr><td><b>Beta</b></td><td>Market Sensitivity</td><td>📈 0.0 - 3.0</td></tr>
        <tr><td><b>Vol Scale</b></td><td>Size Adjustment</td><td>📏 0.0 - 2.0</td></tr>
        <tr><td><b>Kelly Edge</b></td><td>Mathematical Edge</td><td>🔢 0% - 100%</td></tr>
        <tr><td><b>Sector Exp.</b></td><td>Industry Overlap</td><td>🏗️ 0% - 100%</td></tr>
    </table>
    """, unsafe_allow_html=True)

# 4. Data Logic
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"],
                                user=creds["user"], password=creds["password"], sslmode="require")
    except: return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
    df['date_str'] = df['asatdate'].astype(str)
    
    # Standard Pivot
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    
    # 5-Date Slice for UI Matrix
    cols = list(pivot.columns)
    meta_cols = ['symbol', 'sector']
    date_cols = sorted([c for c in cols if c not in meta_cols], reverse=True)[:5]
    pivot_display = pivot[meta_cols + sorted(date_cols)]
    
    return df, pivot_display

raw_df, pivot_5_df = load_data()

# 5. History Popup Logic (Dialog)
@st.dialog("Signal Change History", width="large")
def show_full_history(symbol):
    st.write(f"Showing historical signal changes for **{symbol}**")
    ticker_data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=True)
    
    # Logic: Only keep rows where signal changed from previous date
    ticker_data['signal_changed'] = ticker_data['signal'] != ticker_data['signal'].shift(1)
    changes = ticker_data[ticker_data['signal_changed'] == True].sort_values('asatdate', ascending=False)
    
    st.table(changes[['asatdate', 'signal', 'action', 'notes']].rename(columns={
        'asatdate': 'Date', 'signal': 'Signal', 'action': 'Action', 'notes': 'Reasoning'
    }))

# 6. UI Header
t1, t2, m1, m2 = st.columns([1, 1, 1, 1])
with t1: search = st.text_input("🔍 Ticker", key="s_box").upper()
with t2: sector = st.selectbox("📁 Sector", options=["All"] + sorted(pivot_5_df['sector'].unique().tolist()), key="sec_box")
with m1: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with m2: st.metric("Current Regime", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

with st.expander("📊 Signal Determination Logic"):
    st.markdown("""
    | Signal Level | Conviction | Market Regime | VIX | Action |
    | :--- | :--- | :--- | :--- | :--- |
    | **Extremely Bullish** | > 0.85 | RISK_ON | < 20 | Max Exposure |
    | **Bullish** | 0.60 - 0.84 | RISK_ON | < 28 | Standard Entry |
    | **Neutral** | 0.40 - 0.59 | ANY | ANY | Hold / Wait |
    | **Bearish** | 0.20 - 0.39 | RISK_OFF | > 28 | Reduce / Exit |
    """)

# 7. Main Grid
col_mat, col_intel = st.columns([1.7, 1.3])

filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_mat:
    st.subheader("Recent Signals (Last 5 Active Dates)")
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", width=90)
    gb.configure_column("sector", pinned="left", width=120)
    
    cell_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
        return {backgroundColor: '#F8F9FA', color: '#3C4043'};
    }
    """)
    for c in [x for x in filtered.columns if x not in ['symbol', 'sector']]:
        gb.configure_column(c, cellStyle=cell_style, width=105)
    
    gb.configure_selection(selection_mode="single")
    grid_response = AgGrid(filtered, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=550)

with col_intel:
    sel = grid_response.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        # Detail Header & Audit Button
        c_name, c_btn = st.columns([2, 1])
        with c_name: st.markdown(f"## {ticker}")
        with c_btn: 
            if st.button("📊 View Full History"):
                show_full_history(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Intelligence Date", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # Intelligence Grid
        def row(l, v): st.markdown(f'<div class="grid-row"><span class="grid-label">{l}</span><span class="grid-value">{v}</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="grid-header">PRIMARY SCORES</div>', unsafe_allow_html=True)
        row("Conviction (Hybrid)", f"{d['s_hybrid']:.4f}")
        row("Safety Buffer", f"{(1-d['risk_score']):.4f}")
        row("Financial Strength", f"{d['f_score']:.4f}")
        
        st.markdown('<div class="grid-header">TRADE EXECUTION</div>', unsafe_allow_html=True)
        row("Portfolio Share", f"{d['final_weight']:.2%}")
        row("Cash Required", f"${d['final_dollars']:,}")
        row("Kelly Edge", f"{d['kelly_fraction']:.2%}")

        st.markdown('<div class="grid-header">QUALITATIVE MIX</div>', unsafe_allow_html=True)
        row("Growth/Value Mix", f"{d['gv_score']:.4f}")
        row("Product Pipeline", f"{d['pipeline_score']:.4f}")
        row("Professional Buying", f"{d['smart_money_score']:.4f}")
        row("Wall St. Consensus", f"{d['analyst_score']:.4f}")

        st.markdown('<div class="grid-header">RISK DYNAMICS</div>', unsafe_allow_html=True)
        row("Stock Beta", f"{d['beta']:.2f}")
        row("Volatility Scaling", f"{d['vol_scale']:.2f}")
        row("Sector Exposure", f"{d['sector_weight']:.2%}")
    else:
        st.info("👈 Select a Ticker row to audit details.")
