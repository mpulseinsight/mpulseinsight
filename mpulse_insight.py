import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration - Enterprise Pro
st.set_page_config(page_title="mPulse Pro Insight", layout="wide", initial_sidebar_state="expanded")

# 2. Enterprise Light Theme CSS
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
        header { visibility: hidden; }
        
        /* Light Theme Architecture */
        div[data-testid="column"] { 
            background-color: #ffffff; 
            border: 1px solid #e2e8f0; 
            padding: 15px; 
            border-radius: 8px; 
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
            margin-bottom: 10px;
        }
        
        /* Enterprise Metrics */
        .stMetric { 
            background-color: #f8fafc; 
            border: 1px solid #cbd5e1; 
            border-radius: 4px; 
            padding: 12px !important; 
        }
        
        /* Typography */
        html, body, [class*="ViewContainer"] { font-family: 'Inter', system-ui, sans-serif; color: #1e293b; }
        h1, h2, h3 { color: #0f172a; font-weight: 700; }
        
        /* Corporate Blue Progress Bars */
        .stProgress > div > div > div > div { background-color: #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# 3. Intelligence Legend (Sidebar)
with st.sidebar:
    st.title("📖 Trade Logic")
    with st.expander("Indicator Ranges", expanded=True):
        st.markdown("""
        **0.60 - 1.00:** Strong 🟢
        **0.40 - 0.59:** Neutral 🟡
        **0.00 - 0.39:** Weak 🔴
        """)
        st.caption("**Strength Score:** Conviction level.")
        st.caption("**Safety Buffer:** Protection from volatility.")
        st.caption("**Health:** Fundamental business quality.")
        st.caption("**Smart Money:** Institutional flow.")
    
    with st.expander("Market Climate", expanded=True):
        st.markdown("""
        * **RISK_ON:** High allocation mode.
        * **RISK_OFF:** Defensive/Cash mode.
        * **VIX < 20:** Stability.
        * **VIX > 30:** High Risk/Panic.
        """)

# 4. Database Connection & Data Load
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except Exception as e:
        st.error("❌ DB Connection Failed. Check Secrets.")
        return None

@st.cache_data(ttl=60)
def load_full_data():
    conn = get_db_connection()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    query = "SELECT * FROM mpulse_execution_results WHERE asatdate >= CURRENT_DATE - INTERVAL '30 days' ORDER BY asatdate ASC"
    df = pd.read_sql(query, conn)
    df['date_str'] = df['asatdate'].astype(str)
    # Pivot Table for Timeline
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    return df, pivot

raw_df, pivot_df = load_full_data()

# 5. Dashboard Top Filter Bar
t1, t2, t3, t4 = st.columns([1, 1, 1, 1])
with t1:
    search_query = st.text_input("", placeholder="🔍 Search Ticker...").upper()
with t2:
    all_sectors = ["All Sectors"] + sorted(pivot_df['sector'].unique().tolist())
    sel_sector = st.selectbox("", options=all_sectors, label_visibility="collapsed")
with t3:
    vix_val = raw_df['vix'].iloc[-1] if not raw_df.empty else 0
    st.metric("VIX Index", f"{vix_val:.2f}", delta="Calm" if vix_val < 22 else "Volatile", delta_color="inverse")
with t4:
    regime_val = raw_df['final_regime'].iloc[-1] if not raw_df.empty else "N/A"
    st.metric("Market Regime", regime_val)

# 6. Main UI Layout
col_main, col_intel = st.columns([1.7, 1.3])

# Filtering Pivot
filtered_pivot = pivot_df.copy()
if search_query:
    filtered_pivot = filtered_pivot[filtered_pivot['symbol'].str.contains(search_query)]
if sel_sector != "All Sectors":
    filtered_pivot = filtered_pivot[filtered_pivot['sector'] == sel_sector]

with col_main:
    st.subheader("Signal Matrix")
    gb = GridOptionsBuilder.from_dataframe(filtered_pivot)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=90)
    gb.configure_column("sector", pinned="left", headerName="Sector", width=130)
    
    # Senior Trader Palette: Subtle Greens/Reds
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#f0fdf4', color: '#166534', fontWeight: 'bold'};
        if (val.includes('BEARISH')) return {backgroundColor: '#fef2f2', color: '#991b1b', fontWeight: 'bold'};
        if (val.includes('NEUTRAL')) return {backgroundColor: '#f8fafc', color: '#64748b'};
        return {};
    }
    """)
    
    date_cols = [c for c in filtered_pivot.columns if c not in ['symbol', 'sector']]
    for c in date_cols:
        gb.configure_column(c, cellStyle=signal_style, width=105)

    gb.configure_selection(selection_mode="single")
    gb.configure_grid_options(headerHeight=35, rowHeight=32)
    
    grid_response = AgGrid(filtered_pivot, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=750)

with col_intel:
    # Selection Handling
    selected_rows = grid_response.get('selected_rows')
    has_selection = False
    if selected_rows is not None:
        if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
            has_selection, sel_row = True, selected_rows.iloc[0]
        elif isinstance(selected_rows, list) and len(selected_rows) > 0:
            has_selection, sel_row = True, selected_rows[0]

    if has_selection:
        ticker = sel_row['symbol']
        ticker_hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        
        # Detail Header
        st.markdown(f"## {ticker} <small style='color:#64748b;'>| {sel_row['sector']}</small>", unsafe_allow_html=True)
        date_sel = st.selectbox("Date Log", options=ticker_hist['date_str'].tolist(), label_visibility="collapsed")
        data = ticker_hist[ticker_hist['date_str'] == date_sel].iloc[0]

        # Action Badge (Enterprise Styling)
        act_colors = {"ENTER": "#16a34a", "ACCUMULATE": "#2563eb", "EXIT": "#dc2626", "WAIT": "#475569"}
        act_bg = act_colors.get(data['action'], "#f1f5f9")
        st.markdown(f"""
            <div style="background-color:{act_bg}; padding:12px; border-radius:6px; text-align:center; color:white;">
                <h3 style="margin:0; color:white;">{data['action']}</h3>
                <p style="margin:0; font-size:13px; opacity:0.9;">{data['notes']}</p>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # --- THE INTELLIGENCE RIBBON (Slider Equivalent for Senior Traders) ---
        st.write("### 💎 Key Intelligence")
        
        # Primary Metrics
        m_row1_1, m_row1_2 = st.columns(2)
        m_row1_1.metric("Strength Score", f"{data['s_hybrid']:.2f}", help="Master convicton (0.0 to 1.0)")
        m_row1_2.metric("Safety Buffer", f"{(1 - data['risk_score']):.2f}", help="Stability vs. Volatility")
        
        m_row2_1, m_row2_2 = st.columns(2)
        m_row2_1.metric("Portfolio Weight", f"{data['final_weight']:.1%}", help="Recommended allocation size")
        m_row2_2.metric("Target Cash", f"${data['final_dollars']:,}", help="Cash value of position")

        # Full Data Intelligence Slide-down
        with st.expander("🔍 Comprehensive Field Analysis", expanded=True):
            st.write("**Company & Fundamental Metrics**")
            st.progress(data['f_score'], text=f"Business Health (F-Score): {data['f_score']:.2f}")
            st.progress(data['analyst_score'], text=f"Analyst Sentiment: {data['analyst_score']:.2f}")
            st.progress(data['gv_score'], text=f"Growth/Value Score: {data['gv_score']:.2f}")
            
            st.divider()
            
            st.write("**Sentiment & Momentum**")
            st.progress(data['smart_money_score'], text=f"Institutional Flow: {data['smart_money_score']:.2f}")
            st.progress(data['pipeline_score'], text=f"Pipeline Score: {data['pipeline_score']:.2f}")
            
            st.divider()
            
            st.write("**Market Risk Exposure**")
            st.caption(f"Stock Beta: {data['beta']:.2f} | Vol Scale: {data['vol_scale']:.2f}")
            st.caption(f"Kelly Fraction: {data['kelly_fraction']:.2%} | Sector Penalty: {data['sector_penalty']:.2f}")

        with st.expander("🌏 Market Climate Analysis"):
            st.write(f"Regime: **{data['final_regime']}**")
            st.write(f"VIX: {data['vix']} | Trend: {data['trend_regime']}")
            st.write(f"Sector Weight: {data['sector_weight']:.2%}")

    else:
        st.info("Select a ticker from the matrix to load intelligence data.")
