import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="collapsed")

# 2. THE TOTAL LOCKDOWN & MOBILE FIX (CSS)
st.markdown("""
    <style>
        /* 1. Remove Streamlit Branding & Manage Buttons */
        header { visibility: hidden !important; }
        footer { visibility: hidden !important; }
        #MainMenu { visibility: hidden !important; }
        .stAppDeployButton { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }
        div.viewerBadge_container__1QSob { display: none !important; }

        /* 2. Responsive iPhone Fixes */
        .block-container { padding: 0.5rem 1rem !important; max-width: 100%; }
        
        /* Mobile Column Stacking Logic */
        @media (max-width: 768px) {
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                margin-bottom: 15px;
            }
        }

        /* 3. Professional Card Look */
        div[data-testid="column"] { 
            background-color: #ffffff; border: 1px solid #e0e0e0; 
            padding: 15px; border-radius: 12px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }
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
        st.error("Database Connection Error.")
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

# --- 4. TOP BAR FILTERS ---
t1, t2 = st.columns([1, 1])
with t1:
    search_symbol = st.text_input("🔍 Find Ticker", placeholder="Search...").upper()
with t2:
    all_sectors = ["All Categories"] + sorted(pivot_df['sector'].unique().tolist())
    selected_sector = st.selectbox("📁 Category", options=all_sectors)

filtered_pivot = pivot_df.copy()
if search_symbol:
    filtered_pivot = filtered_pivot[filtered_pivot['symbol'].str.contains(search_symbol)]
if selected_sector != "All Categories":
    filtered_pivot = filtered_pivot[filtered_pivot['sector'] == selected_sector]

# --- 5. MAIN INTERFACE ---
col_grid, col_info = st.columns([1.8, 1.2])

with col_grid:
    gb = GridOptionsBuilder.from_dataframe(filtered_pivot)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=90)
    gb.configure_column("sector", pinned="left", headerName="Category", width=120)
    
    # Lighter Professional Heatmap
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#f0fdf4', color: '#166534', borderRight: '1px solid #f1f5f9'};
        if (val.includes('BEARISH')) return {backgroundColor: '#fef2f2', color: '#991b1b', borderRight: '1px solid #f1f5f9'};
        return {backgroundColor: '#f8f9fa', color: '#475569', borderRight: '1px solid #f1f5f9'};
    }
    """)

    date_cols = [col for col in filtered_pivot.columns if col not in ['sector', 'symbol']]
    for c in date_cols:
        gb.configure_column(c, cellStyle=signal_style, width=105)

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(headerHeight=40, rowHeight=35)
    
    grid_response = AgGrid(filtered_pivot, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=500)

with col_info:
    selected = grid_response.get('selected_rows')
    if selected is not None and len(selected) > 0:
        row = selected.iloc[0] if isinstance(selected, pd.DataFrame) else selected[0]
        ticker = row['symbol']
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        
        st.markdown(f"### 📈 {ticker} Plan")
        sel_date = st.selectbox("Select Date", options=hist['date_str'].tolist(), label_visibility="collapsed")
        data = hist[hist['date_str'] == sel_date].iloc[0]

        # METRICS WITH HUMAN LABELS & DESCRIPTIONS
        st.metric("Strength Score", f"{data['s_hybrid']:.2f}", help="Calculated market health. Above 0.60 is Bullish.")
        
        m1, m2 = st.columns(2)
        m1.metric("Safety Buffer", f"{data['kelly_fraction']:.1%}", help="How much protection you have against market swings.")
        m2.metric("Portfolio Share", f"{data['final_weight']:.1%}", help="Recommended percentage of your total funds.")
        
        st.metric("Cash to Use", f"${data['final_dollars']:,}", help="The actual dollar amount suggested for this trade.")

        # Threshold Guideline Table
        st.markdown("---")
        with st.expander("📖 Investment Guide & Thresholds", expanded=False):
            st.write("""
            | Metric | Good Range | Meaning |
            | :--- | :--- | :--- |
            | **Strength** | 0.60 - 1.0 | Strong pulse, high confidence. |
            | **Safety** | 10% - 25% | Healthy room for error. |
            | **Company** | 7.0+ | Business is making money. |
            | **Sentiment** | Positive | Big players are buying. |
            | **Market Risk** | Low/Med | Environment is safe for entry. |
            """)
    else:
        st.info("👋 Select a ticker from the left to view the investment plan.")

# --- 6. GLOBAL GLOSSARY (Informative Section) ---
st.divider()
st.subheader("How to read the mPulse Terminal")
g1, g2, g3 = st.columns(3)

with g1:
    st.markdown("**Strength Score**")
    st.caption("A combined measure of price speed and volume. Higher numbers mean the stock is in a confirmed 'Up' cycle.")

with g2:
    st.markdown("**Safety Buffer**")
    st.caption("Think of this as your seatbelt. It tells you how much capital is safe to risk based on current volatility.")

with g3:
    st.markdown("**Market Sentiment**")
    st.caption("Tracks whether Institutional 'Smart Money' is quietly accumulating or selling their shares.")
