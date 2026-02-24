import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="expanded")

# 2. Refined CSS (Cleaner, focused on readability)
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #FFFFFF; color: #202124; }
        .block-container { padding-top: 1.5rem !important; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-size: 24px !important; }
        [data-testid="stMetricLabel"] { font-weight: 700 !important; color: #5F6368 !important; }
        /* Remove whitespace from the top of the columns */
        div[data-testid="column"] { padding: 0px 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. Friendly Factor Dictionary
FACTOR_MAP = {
    's_hybrid': ('Daily Market Pulse', 'Short-term confidence based on today\'s momentum.'),
    's_structural': ('60-Day Foundation', 'Long-term stability and growth trajectory.'),
    'f_score': ('Financial Strength', 'How healthy the company\'s bank account/debt looks.'),
    'smart_money_score': ('Institutional Following', 'Tracking if the "Big Banks" are buying.'),
    'analyst_score': ('Wall Street Consensus', 'Professional analysts\' average opinion.'),
    'pipeline_score': ('Business Pipeline', 'Future inventory and project momentum.'),
    'gv_score': ('Price-to-Value', 'Is the stock currently "on sale" or expensive?'),
    'risk_score': ('Danger Level', 'Likelihood of a sharp sudden drop.'),
    'sector_strength': ('Industry Health', 'Performance of the "neighborhood" (Sector) this stock lives in.')
}

# 4. Data Engine (Direct-to-Close Logic)
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require",
            connect_timeout=10
        )
    except Exception as e:
        st.error(f"⚠️ Connection Failed: {e}")
        return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    
    try:
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate DESC", conn)
    finally:
        conn.close()

    if df.empty: return pd.DataFrame(), pd.DataFrame()

    df['date_str'] = df['asatdate'].astype(str)
    
    # Grid Pivot: Limit to top 5 most recent dates horizontally
    pivot_col = 'execution_stance' if 'execution_stance' in df.columns else 'signal'
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                           values=pivot_col, aggfunc='first').reset_index().fillna('')
    
    # Slice only the 5 most recent date columns
    all_dates = sorted([c for c in pivot.columns if c not in ['symbol', 'sector']], reverse=True)
    top_5_dates = sorted(all_dates[:5])
    
    return df, pivot[['symbol', 'sector'] + top_5_dates]

# --- LOAD DATA ---
with st.spinner("Fetching latest intelligence..."):
    raw_df, pivot_5_df = load_data()

if raw_df.empty:
    st.warning("No data found. Check database connection.")
    st.stop()

# 5. Dashboard Top Navigation
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Find Ticker", placeholder="e.g. NVDA").upper()
with m2: 
    sec_list = ["All Industries"] + sorted(raw_df['sector'].unique().tolist())
    selected_sector = st.selectbox("📂 Industry View", options=sec_list)
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[0]:.2f}")
with m4: st.metric("Market Weather", f"{raw_df['final_regime'].iloc[0]}")

# 6. Main Content Split
col_grid, col_intel = st.columns([1.4, 1.6])

# Filter Grid Data
filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if selected_sector != "All Industries": filtered = filtered[filtered['sector'] == selected_sector]

with col_grid:
    # Header "Matrix: Execution Stance" removed as requested
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", width=95, header_name="Ticker")
    gb.configure_column("sector", width=120, header_name="Industry")
    
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
        if c not in ['symbol', 'sector']:
            gb.configure_column(c, cellStyle=js_style, width=110)
    
    gb.configure_selection(selection_mode="single")
    grid_out = AgGrid(filtered, gridOptions=gb.build(), allow_unsafe_jscode=True, 
                      update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine", height=600)

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row['symbol']
        
        # Get specific data for selected ticker
        d = raw_df[raw_df['symbol'] == ticker].iloc[0]
        
        # Action Header
        c_name, c_hist = st.columns([2, 1])
        with c_name: st.markdown(f"<h2 style='margin:0;'>{ticker} Analysis</h2>", unsafe_allow_html=True)
        with c_hist: 
            if st.button("📊 View Full History"):
                # Simple expander/dialog logic for history
                st.info(f"Showing last 10 entries for {ticker}")
                st.dataframe(raw_df[raw_df['symbol'] == ticker][['asatdate', 'signal', 'suggested_action']].head(10))

        # Action Badge
        st.markdown(f"""
            <div style="background-color: #E8F0FE; padding: 15px; border-radius: 8px; border-left: 5px solid #1A73E8; margin-top:10px;">
                <p style="margin:0; font-size:12px; color:#5F6368; font-weight:bold;">STRATEGY RECOMMENDATION</p>
                <h3 style="margin:0; color:#1A73E8;">{d['suggested_action']} ({d['execution_stance']})</h3>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🔍 Key Health Factors")
        
        # Common Man Explanations Layout
        def factor_card(key, current_val):
            name, desc = FACTOR_MAP.get(key, (key, "Score detail"))
            # Invert risk score for display so "High" means "Safe"
            display_val = (1 - current_val) if key == 'risk_score' else current_val
            
            with st.container():
                st.markdown(f"**{name}**")
                st.markdown(f"<p style='font-size:12px; color:#5F6368; margin-top:-10px;'>{desc}</p>", unsafe_allow_html=True)
                st.progress(min(max(float(display_val), 0.0), 1.0))
                st.markdown(f"<p style='text-align:right; font-size:11px; margin-top:-5px;'>Current Level: {display_val:.2f}</p>", unsafe_allow_html=True)

        i1, i2 = st.columns(2)
        with i1:
            factor_card('s_hybrid', d['s_hybrid'])
            factor_card('smart_money_score', d['smart_money_score'])
            factor_card('f_score', d['f_score'])
            factor_card('sector_strength', d.get('sector_strength', 0))
        with i2:
            factor_card('s_structural', d.get('s_structural', 0))
            factor_card('analyst_score', d['analyst_score'])
            factor_card('gv_score', d['gv_score'])
            factor_card('risk_score', d['risk_score'])

        # Final Allocation Math
        st.markdown("---")
        with st.expander("💰 Capital Allocation Detail"):
            st.write(f"This trade uses **{d['final_weight']:.2%}** of total capital.")
            st.write(f"Based on your book value, the suggested size is **${d['final_dollars']:,}**.")
    else:
        st.markdown("""
            <div style="padding:40px; border: 2px dashed #DADCE0; border-radius:10px; text-align:center; color:#5F6368; margin-top:20px;">
                <h3>Select a Ticker</h3>
                <p>Click on a row in the matrix to see the plain-English factor analysis.</p>
            </div>
        """, unsafe_allow_html=True)
