import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration - Extreme High Density
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="collapsed")

# 2. Ultra-Modern Professional CSS
st.markdown("""
    <style>
        /* Main Container Optimization */
        .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 98%; }
        header { visibility: hidden; }
        
        /* Dark Theme Styling */
        div[data-testid="column"] { 
            background-color: #0d1117; 
            border: 1px solid #30363d; 
            padding: 15px; 
            border-radius: 8px; 
            margin-bottom: 10px;
        }
        
        /* Metric Styling */
        .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px !important; }
        
        /* Scannability for Mobile */
        @media (max-width: 768px) {
            div[data-testid="column"] { padding: 8px; margin-bottom: 5px; }
            .stMetric { padding: 5px !important; }
        }
        
        /* Custom Progress Bar Color */
        .stProgress > div > div > div > div { background-color: #58a6ff; }
    </style>
""", unsafe_allow_html=True)

# 3. Database Connection
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except Exception as e:
        st.error("❌ Database connection failed.")
        return None

@st.cache_data(ttl=60)
def load_full_data():
    conn = get_db_connection()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    query = "SELECT * FROM mpulse_execution_results WHERE asatdate >= CURRENT_DATE - INTERVAL '30 days' ORDER BY asatdate ASC"
    df = pd.read_sql(query, conn)
    df['date_str'] = df['asatdate'].astype(str)
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    return df, pivot

raw_df, pivot_df = load_full_data()

# --- 4. TOP SUMMARY BAR (Information at a Glance) ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    vix_val = raw_df['vix'].iloc[-1] if not raw_df.empty else 0
    st.metric("Market Fear (VIX)", f"{vix_val:.2f}", delta="Risk-On" if vix_val < 22 else "Risk-Off", delta_color="inverse")
with m2:
    active_signals = raw_df[raw_df['asatdate'] == raw_df['asatdate'].max()]
    bullish_count = len(active_signals[active_signals['signal'].str.contains("BULLISH", na=False)])
    st.metric("Bullish Opportunities", bullish_count)
with m3:
    search_query = st.text_input("", placeholder="🔍 Search Ticker...").upper()
with m4:
    sector_list = ["All Sectors"] + sorted(pivot_df['sector'].unique().tolist())
    sel_sector = st.selectbox("", options=sector_list, label_visibility="collapsed")

# --- 5. MAIN UI LAYOUT ---
col_timeline, col_detail = st.columns([1.8, 1.2])

# Filter Logic
filtered_pivot = pivot_df.copy()
if search_query:
    filtered_pivot = filtered_pivot[filtered_pivot['symbol'].str.contains(search_query)]
if sel_sector != "All Sectors":
    filtered_pivot = filtered_pivot[filtered_pivot['sector'] == sel_sector]

with col_timeline:
    gb = GridOptionsBuilder.from_dataframe(filtered_pivot)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=90)
    gb.configure_column("sector", pinned="left", headerName="Sector", width=130)
    
    # Heatmap Logic
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#064e3b', color: '#ecfdf5', fontWeight: 'bold'};
        if (val.includes('BEARISH')) return {backgroundColor: '#7f1d1d', color: '#fef2f2', fontWeight: 'bold'};
        if (val.includes('NEUTRAL')) return {backgroundColor: '#1e293b', color: '#f1f5f9'};
        return {};
    }
    """)
    
    date_cols = [c for c in filtered_pivot.columns if c not in ['symbol', 'sector']]
    for c in date_cols:
        gb.configure_column(c, cellStyle=signal_style, width=105)

    gb.configure_selection(selection_mode="single")
    gb.configure_grid_options(headerHeight=35, rowHeight=32)
    
    grid_response = AgGrid(filtered_pivot, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=700)

with col_detail:
    # Logic to capture selection
    selected_rows = grid_response.get('selected_rows')
    has_selection = False
    if selected_rows is not None:
        if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
            has_selection, sel_row = True, selected_rows.iloc[0]
        elif isinstance(selected_rows, list) and len(selected_rows) > 0:
            has_selection, sel_row = True, selected_rows[0]

    if has_selection:
        ticker = sel_row['symbol']
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        
        # Sub-header with ticker details
        st.markdown(f"## {ticker} <small style='color:gray'>{sel_row['sector']}</small>", unsafe_allow_html=True)
        date_pick = st.selectbox("Historical View", options=hist['date_str'].tolist(), label_visibility="collapsed")
        data = hist[hist['date_str'] == date_pick].iloc[0]

        # --- ACTION CARD ---
        action_colors = {"ENTER": "#064e3b", "ACCUMULATE": "#1e3a8a", "EXIT": "#7f1d1d", "WAIT": "#44403c"}
        bg = action_colors.get(data['action'], "#161b22")
        st.markdown(f"""
            <div style="background-color:{bg}; padding:15px; border-radius:10px; text-align:center; border: 1px solid #30363d">
                <h2 style="margin:0; color:white;">{data['action']}</h2>
                <p style="margin:0; opacity:0.9; font-size:14px;">{data['notes']}</p>
            </div>
        """, unsafe_allow_html=True)

        st.write("### 💎 Logic Breakdown")
        
        # Core 4 Fields (Common Man Mappings)
        c1, c2 = st.columns(2)
        c1.metric("Strength Score", f"{data['s_hybrid']:.2f}", help="Conviction level (0-1)")
        c2.metric("Safety Buffer", f"{(1 - data['risk_score']):.2f}", help="Higher is safer (Inverted Risk)")
        
        c3, c4 = st.columns(2)
        c3.metric("Portfolio Share", f"{data['final_weight']:.1%}")
        c4.metric("Cash to Use", f"${data['final_dollars']:,}")

        # Visual Score Drivers
        with st.expander("🔍 Diagnostic Scores", expanded=True):
            # Fundamental Health
            st.write(f"**Business Health (F-Score):** {data['f_score']:.2f}")
            st.progress(data['f_score'])
            
            # Smart Money
            st.write(f"**Smart Money Flow:** {data['smart_money_score']:.2f}")
            st.progress(data['smart_money_score'])
            
            # Analysts
            st.write(f"**Analyst Sentiment:** {data['analyst_score']:.2f}")
            st.progress(data['analyst_score'])

        # Context Info
        with st.expander("🌍 Market Context"):
            st.write(f"**Regime:** {data['final_regime']}")
            st.write(f"**Volatility:** {data['vix']} (VIX)")
            st.write(f"**Trend Mode:** {data['trend_regime']}")
            st.caption(f"Kelly Fraction: {data['kelly_fraction']:.2%}")
    else:
        st.info("👈 Select a ticker to view its intelligence profile.")
