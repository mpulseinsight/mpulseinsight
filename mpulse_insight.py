import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="expanded")

# 2. Factor & Terminology Dictionary
# This maps technical columns to "Common Man" terms + explains the 0.0-1.0 range
DICTIONARY = {
    "Factors": {
        "s_hybrid": ["Daily Market Pulse", "0.0 - 1.0", "Short-term momentum. Above 0.70 is a 'Buy' signal."],
        "s_structural": ["60-Day Foundation", "0.0 - 1.0", "Long-term trend. 0.60+ suggests a solid multi-month hold."],
        "f_score": ["Financial Health", "0.0 - 1.0", "Company safety. Higher means better balance sheets/profits."],
        "smart_money_score": ["Institutional Buy-in", "0.0 - 1.0", "Shows if hedge funds and big banks are moving in."],
        "risk_score": ["Danger Level", "0.0 - 1.0", "Lower is safer. We invert this on the bar for you (Safe = Full Bar)."],
        "sector_strength": ["Industry Support", "0 - 100%", "Breadth of the sector. High % means the whole group is rising."]
    },
    "Terminology": {
        "CORE_LONG": "The 'Gold Standard'. Both daily momentum and 60-day trends are perfectly aligned.",
        "STRUCTURAL": "A marathon runner. This is a long-term play based on fundamental health.",
        "TACTICAL": "A sprinter. Quick move based on a daily price bounce.",
        "EXHAUSTED": "The stock has run too far, too fast. Risk of a pullback is high."
    }
}

# 3. Popup: Full History Dialog
@st.dialog("Activity Log & Audit Trail", width="large")
def show_history_popup(ticker, raw_data):
    st.markdown(f"### Historical Performance: {ticker}")
    history = raw_data[raw_data['symbol'] == ticker].sort_values('asatdate', ascending=False)
    
    # Selecting columns that matter for history
    view_cols = ['asatdate', 'execution_stance', 'suggested_action', 'final_weight', 's_hybrid', 's_structural']
    formatted_hist = history[view_cols].rename(columns={
        'asatdate': 'Date', 'execution_stance': 'Strategy', 
        'suggested_action': 'Action', 'final_weight': 'Alloc %'
    })
    
    st.dataframe(formatted_hist, use_container_width=True, hide_index=True)
    st.caption("Showing the most recent activity records from the database.")

# 4. Data Engine
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except: return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    try:
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate DESC", conn)
    finally: conn.close()
    
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    
    df['date_str'] = df['asatdate'].astype(str)
    all_dates = sorted(df['date_str'].unique().tolist(), reverse=True)[:5]
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                           values='execution_stance', aggfunc='first').reset_index().fillna('')
    return df, pivot[['symbol', 'sector'] + sorted(all_dates)]

# --- LOAD DATA ---
raw_df, pivot_5_df = load_data()

# 5. Sidebar Dictionary (The "Cheat Sheet")
with st.sidebar:
    st.header("📖 Master Dictionary")
    
    with st.expander("🛡️ Strategies Explained", expanded=True):
        for term, desc in DICTIONARY["Terminology"].items():
            st.markdown(f"**{term}**: {desc}")
            
    with st.expander("📊 Factor Meanings", expanded=False):
        for key, val in DICTIONARY["Factors"].items():
            st.markdown(f"**{val[0]}**")
            st.caption(f"Range: {val[1]} | {val[2]}")
            st.markdown("---")

# 6. Main UI Layout
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Search Ticker").upper()
with m2: sector = st.selectbox("📁 Industry", ["All"] + sorted(raw_df['sector'].unique().tolist()))
with m3: st.metric("Market Fear", f"{raw_df['vix'].iloc[0]:.1f}")
with m4: st.metric("Market Regime", raw_df['final_regime'].iloc[0])

col_grid, col_intel = st.columns([1.4, 1.6])

# Filter logic
filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", header_name="Ticker")
    
    # Custom colors for strategies
    js_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('CORE_LONG')) return {backgroundColor: '#FEF7E0', color: '#B06000', fontWeight: 'bold'};
        if (v.includes('STRUCTURAL')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('TACTICAL')) return {backgroundColor: '#E8F0FE', color: '#1A73E8', fontWeight: 'bold'};
        return {backgroundColor: '#F8F9FA', color: '#5F6368'};
    }
    """)
    for c in filtered.columns:
        if c not in ['symbol', 'sector']: gb.configure_column(c, cellStyle=js_style)
    
    gb.configure_selection(selection_mode="single")
    grid_out = AgGrid(filtered, gridOptions=gb.build(), allow_unsafe_jscode=True, 
                      update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine", height=600)

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row['symbol']
        d = raw_df[raw_df['symbol'] == ticker].iloc[0]
        
        # Action Header
        c_name, c_btn = st.columns([2, 1])
        with c_name: st.markdown(f"## {ticker} Intel")
        with c_btn: 
            if st.button("📊 View History"): show_history_popup(ticker, raw_df)
            
        # Strategy Badge
        st.info(f"**Action:** {d['suggested_action']} | **Stance:** {d['execution_stance']}")

        # Display Factors
        st.markdown("### 🔍 Health Check")
        i1, i2 = st.columns(2)
        
        # Visualizing the factors using the Dictionary
        def draw_factor(key, val):
            label = DICTIONARY["Factors"][key][0]
            # Handle the inverted risk score visually
            bar_val = (1 - val) if key == 'risk_score' else val
            st.markdown(f"**{label}**")
            st.progress(min(max(float(bar_val), 0.0), 1.0))
            st.caption(f"Score: {val:.2f}")

        with i1:
            draw_factor('s_hybrid', d['s_hybrid'])
            draw_factor('f_score', d['f_score'])
            draw_factor('sector_strength', d.get('sector_strength', 0))
        with i2:
            draw_factor('s_structural', d.get('s_structural', 0))
            draw_factor('smart_money_score', d['smart_money_score'])
            draw_factor('risk_score', d['risk_score'])
            
        st.markdown("---")
        st.markdown(f"**Allocation Math:** Uses {d['final_weight']:.2%} of capital (${d['final_dollars']:,})")
    else:
        st.write("Please select a ticker to view details.")
