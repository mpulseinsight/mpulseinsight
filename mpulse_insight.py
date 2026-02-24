import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Tech Dictionary for the "Deep Dive" Window
TECH_DEFS = {
    "Score Group": {
        "s_hybrid": ["Daily Momentum Score", "0.0 - 1.0", "Combines F, gV, Smart Money, and Analysts for today."],
        "s_structural": ["60-Day Foundation", "0.0 - 1.0", "Long-term strength (Pipeline + F-Score + Sector)."],
        "f_score": ["Financial Score", "0.0 - 1.0", "Fundamental health based on balance sheet."],
        "gv_score": ["Growth/Value Score", "0.0 - 1.0", "Valuation metric (is it cheap or expensive?)."],
        "smart_money_score": ["Smart Money Flow", "0.0 - 1.0", "Institutional accumulation tracking."],
        "risk_score": ["Raw Risk Level", "0.0 - 1.0", "Higher = more dangerous. Used to penalize position size."]
    },
    "Execution Stats": {
        "beta": ["Beta", "0.1 - 3.0", "Sensitivity to market. High beta means high volatility."],
        "vol_scale": ["Volatility Scaler", "0.5 - 1.2", "Adjustment factor: 1.0/Beta."],
        "kelly_fraction": ["Kelly Fraction", "0% - 100%", "The raw confidence based on regime and scores."],
        "sector_penalty": ["Sector Penalty", "0.5 or 1.0", "Multiplier: 0.5 if industry breadth is weak (<30%)."],
        "final_weight": ["Final Allocation", "0% - 5%", "The actual portfolio % weight suggested."]
    }
}

# 3. Popup: Technical Audit Dialog (The "Maximum Fields" Reference)
@st.dialog("Technical Deep Dive", width="large")
def show_tech_audit(ticker, raw_data):
    st.markdown(f"### Technical Audit: {ticker}")
    # Get the single most recent record for this ticker
    d = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    
    col1, col2 = st.columns(2)
    for i, (group, items) in enumerate(TECH_DEFS.items()):
        target_col = col1 if i % 2 == 0 else col2
        with target_col:
            st.subheader(group)
            for key, val in items.items():
                current_val = d.get(key, "N/A")
                st.markdown(f"**{val[0]}** (`{key}`)")
                st.markdown(f"Value: `{current_val}` | Range: {val[1]}")
                st.caption(val[2])
                st.markdown("---")

# 4. Popup: Full History Dialog
@st.dialog("Activity Log", width="large")
def show_history_popup(ticker, raw_data):
    st.markdown(f"### History: {ticker}")
    # Sorted by tradedate now
    hist = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False)
    st.dataframe(hist[['tradedate', 'signal', 'signal_60d', 'execution_stance', 'final_weight']], 
                 use_container_width=True, hide_index=True)

# 5. Data Engine (Switching asatdate -> tradedate)
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
    try:
        # We order by tradedate for the timeline
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate ASC", conn)
    finally: conn.close()
    if df.empty: return pd.DataFrame(), pd.DataFrame()

    # --- UPDATED: Using tradedate for the horizontal axis ---
    df['date_str'] = df['tradedate'].astype(str)
    df['combined_signal'] = df['signal'] + " | " + df['signal_60d']
    
    # Get last 5 TRADING dates
    all_dates = sorted(df['date_str'].unique().tolist(), reverse=True)[:5]
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                           values='combined_signal', aggfunc='first').reset_index().fillna('')
    return df, pivot[['symbol', 'sector'] + sorted(all_dates)]

raw_df, pivot_5_df = load_data()

# 6. Sidebar Dictionary
with st.sidebar:
    st.header("📖 Quick Reference")
    st.info("**CORE_LONG**: Perfect Alignment\n\n**STRUCTURAL**: 60D Trend Play\n\n**TACTICAL**: Daily Price Move")

# 7. UI Headers
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Ticker Search").upper()
with m2: sector = st.selectbox("📂 Industry", ["All"] + sorted(raw_df['sector'].unique().tolist()))
with m3: st.metric("VIX", f"{raw_df['vix'].iloc[-1]:.1f}")
with m4: st.metric("Market Regime", raw_df['final_regime'].iloc[-1])

col_grid, col_intel = st.columns([1.5, 1.5])

# Filtering
filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    # No header as requested
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", header_name="Ticker")
    
    # Cell Styling Logic
    js_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('BUY')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('BULLISH')) return {backgroundColor: '#E8F0FE', color: '#1A73E8'};
        return {backgroundColor: '#F8F9FA', color: '#5F6368'};
    }
    """)
    for c in filtered.columns:
        if c not in ['symbol', 'sector']: 
            gb.configure_column(c, cellStyle=js_style, width=190)
    
    gb.configure_selection(selection_mode="single")
    grid_out = AgGrid(filtered, gridOptions=gb.build(), allow_unsafe_jscode=True, 
                      update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine", height=600)

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row['symbol']
        # Get latest data for this ticker based on TRADEDATE
        d = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
        
        st.markdown(f"## {ticker} Intel")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📊 View Log"): show_history_popup(ticker, raw_df)
        with b2:
            if st.button("🔬 Technical Audit"): show_tech_audit(ticker, raw_df)
            
        st.success(f"**Strategy:** {d['execution_stance']} | **Action:** {d['suggested_action']}")

        # Dual Signal Breakdown
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Daily Signal**")
            st.markdown(f"<h4 style='color:#1A73E8;'>{d['signal']}</h4>", unsafe_allow_html=True)
        with c2:
            st.markdown("**60-Day Signal**")
            st.markdown(f"<h4 style='color:#137333;'>{d['signal_60d']}</h4>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Decision Scores")
        st.progress(float(d['s_hybrid']), text=f"Daily Pulse: {d['s_hybrid']:.2f}")
        st.progress(float(d.get('s_structural', 0)), text=f"60-Day Foundation: {d.get('s_structural', 0):.2f}")
        
        st.write(f"**Current Capital Allocation:** {d['final_weight']:.2%}")
    else:
        st.info("Select a ticker row to see the combined Daily/60D intelligence.")
