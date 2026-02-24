import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Tech Dictionary Reference (For the Deep Dive window)
TECH_DEFS = {
    "Score Group": {
        "s_hybrid": ["Daily Momentum Score", "0.0 - 1.0", "Combines F, gV, Smart Money, and Analysts for today."],
        "s_structural": ["60-Day Foundation", "0.0 - 1.0", "Long-term strength (Pipeline + F-Score + Sector)."],
        "f_score": ["Financial Score", "0.0 - 1.0", "Fundamental health based on balance sheet."],
        "gv_score": ["Growth/Value Score", "0.0 - 1.0", "Valuation metric (is it cheap or expensive?)."]
    },
    "Execution Stats": {
        "beta": ["Beta", "0.1 - 3.0", "Sensitivity to market. High beta means high volatility."],
        "final_weight": ["Final Allocation", "0% - 5%", "The actual portfolio % weight suggested."]
    }
}

# 3. Popups (Audit & History)
@st.dialog("Technical Deep Dive", width="large")
def show_tech_audit(ticker, raw_data):
    st.markdown(f"### Technical Audit: {ticker}")
    d = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    col1, col2 = st.columns(2)
    for i, (group, items) in enumerate(TECH_DEFS.items()):
        target_col = col1 if i % 2 == 0 else col2
        with target_col:
            st.subheader(group)
            for key, val in items.items():
                st.markdown(f"**{val[0]}**: `{d.get(key, 'N/A')}`")
                st.caption(f"Range: {val[1]} | {val[2]}")
                st.markdown("---")

@st.dialog("Activity Log", width="large")
def show_history_popup(ticker, raw_data):
    st.markdown(f"### History: {ticker}")
    hist = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False)
    st.dataframe(hist[['tradedate', 'signal', 'signal_60d', 'execution_stance', 'final_weight']], use_container_width=True, hide_index=True)

# 4. Data Engine (Cached)
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], user=creds["user"], password=creds["password"], sslmode="require")
    except: return None

@st.cache_data(ttl=60)
def load_raw_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate ASC", conn)
    finally: conn.close()
    return df

# 5. UI Controls (Sidebar)
with st.sidebar:
    st.header("🛠️ Grid Controls")
    st.write("Choose what to see in the cells:")
    show_daily = st.checkbox("Daily Perspective", value=True)
    show_60d = st.checkbox("60-Day Perspective", value=True)
    
    st.markdown("---")
    st.header("📖 Strategy Key")
    st.info("**TACTICAL**: Daily Focus\n\n**STRUCTURAL**: 60D Focus\n\n**CORE_LONG**: Aligned")

# 6. Logic to Process Grid based on Checkboxes
raw_df = load_raw_data()

if not raw_df.empty:
    # Prepare the display string based on checkboxes
    def get_display_val(row):
        parts = []
        if show_daily: parts.append(str(row['signal']))
        if show_60d: parts.append(f"🛡️ {row['signal_60d']}")
        return " | ".join(parts) if parts else "---"

    raw_df['display_signal'] = raw_df.apply(get_display_val, axis=1)
    raw_df['date_str'] = raw_df['tradedate'].astype(str)
    
    # Pivot for the grid
    all_dates = sorted(raw_df['date_str'].unique().tolist(), reverse=True)[:5]
    pivot_df = raw_df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                                  values='display_signal', aggfunc='first').reset_index().fillna('')
    pivot_df = pivot_df[['symbol', 'sector'] + sorted(all_dates)]

# 7. Dashboard Layout
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Ticker").upper()
with m2: sector = st.selectbox("📂 Industry", ["All"] + sorted(raw_df['sector'].unique().tolist()))
with m3: st.metric("VIX", f"{raw_df['vix'].iloc[-1]:.1f}")
with m4: st.metric("Regime", raw_df['final_regime'].iloc[-1])

col_grid, col_intel = st.columns([1.6, 1.4])

# Filtering
filtered = pivot_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", header_name="Ticker", width=100)
    
    # Dynamic styling and width based on checkbox state
    cell_width = 190 if (show_daily and show_60d) else 120
    
    js_style = JsCode("""
    function(params) {
        if (!params.value || params.value === '---') return {};
        const v = params.value.toUpperCase();
        if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
        return {backgroundColor: '#F8F9FA', color: '#5F6368'};
    }
    """)
    
    for c in filtered.columns:
        if c not in ['symbol', 'sector']: 
            gb.configure_column(c, cellStyle=js_style, width=cell_width)
    
    gb.configure_selection(selection_mode="single")
    grid_out = AgGrid(filtered, gridOptions=gb.build(), allow_unsafe_jscode=True, 
                      update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine", height=600)

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row['symbol']
        d = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
        
        st.markdown(f"## {ticker} Intel")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📊 View Log"): show_history_popup(ticker, raw_df)
        with b2:
            if st.button("🔬 Technical Audit"): show_tech_audit(ticker, raw_df)
            
        st.success(f"**Strategy:** {d['execution_stance']} | **Action:** {d['suggested_action']}")

        # Visual Signal Breakdown
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Daily Signal**")
            st.markdown(f"<h3 style='color:#1A73E8;'>{d['signal']}</h3>", unsafe_allow_html=True)
        with c2:
            st.markdown("**60-Day Signal**")
            st.markdown(f"<h3 style='color:#137333;'>{d['signal_60d']}</h3>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Confidence Scores")
        st.progress(float(d['s_hybrid']), text=f"Daily Pulse: {d['s_hybrid']:.2f}")
        st.progress(float(d.get('s_structural', 0)), text=f"60-Day Foundation: {d.get('s_structural', 0):.2f}")
    else:
        st.info("Select a ticker row to see the combined Daily/60D intelligence.")
