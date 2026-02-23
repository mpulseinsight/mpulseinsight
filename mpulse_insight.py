import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="collapsed")

# 2. Professional UI Styling (Lighter Colors & Responsive Tweaks)
st.markdown("""
    <style>
        /* Modern Background & Font */
        .block-container { padding-top: 0.5rem; padding-bottom: 0rem; max-width: 98%; }
        header { visibility: hidden; }
        
        /* Professional Card Styling */
        div[data-testid="column"] { 
            background-color: #ffffff; border: 1px solid #e0e0e0; 
            padding: 12px; border-radius: 12px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Metric Styling - Common Man Labels */
        [data-testid="stMetricValue"] { font-size: 1.2rem !important; color: #1a73e8; }
        [data-testid="stMetricLabel"] { font-weight: 600; color: #5f6368; }

        /* Clean Heatmap Colors */
        .ag-theme-alpine { --ag-header-background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except Exception as e:
        st.error("Connection failed. Check settings.")
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

# --- 3. TOP FILTER BAR ---
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

# --- 4. RESPONSIVE LAYOUT ---
# On mobile, the details will naturally stack. We keep columns for Desktop.
col_grid, col_info = st.columns([2, 1])

with col_grid:
    gb = GridOptionsBuilder.from_dataframe(filtered_pivot)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=90)
    gb.configure_column("sector", pinned="left", headerName="Category", width=120)
    
    # LIGHTER PROFESSIONAL COLORS
    # Bullish: Soft Emerald | Bearish: Soft Rose | Neutral: Slate Gray
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#e6fffa', color: '#065f46', fontSize: '12px'};
        if (val.includes('BEARISH')) return {backgroundColor: '#fff5f5', color: '#9b2c2c', fontSize: '12px'};
        return {backgroundColor: '#f8f9fa', color: '#4a5568', fontSize: '12px'};
    }
    """)

    date_cols = [col for col in filtered_pivot.columns if col not in ['sector', 'symbol']]
    for c in date_cols:
        gb.configure_column(c, cellStyle=signal_style, width=105)

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(headerHeight=35, rowHeight=32)
    
    grid_response = AgGrid(filtered_pivot, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=500)

with col_info:
    selected = grid_response.get('selected_rows')
    if selected is not None and len(selected) > 0:
        row = selected.iloc[0] if isinstance(selected, pd.DataFrame) else selected[0]
        ticker = row['symbol']
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        
        st.subheader(f"📊 {ticker} Analysis")
        sel_date = st.selectbox("History", options=hist['date_str'].tolist(), label_visibility="collapsed")
        data = hist[hist['date_str'] == sel_date].iloc[0]

        # HUMAN FRIENDLY LABELS
        # Hybrid -> Growth Score
        # Kelly -> Safety Buffer
        # Weight -> Portfolio Share
        # Value -> Cash to Invest
        
        m1, m2 = st.columns(2)
        m1.metric("Strength Score", f"{data['s_hybrid']:.2f}")
        m2.metric("Safety Buffer", f"{data['kelly_fraction']:.1%}")
        
        m3, m4 = st.columns(2)
        m3.metric("Plan Share", f"{data['final_weight']:.1%}")
        m4.metric("Cash to Use", f"${data['final_dollars']:,}")

        with st.expander("Smart Insights"):
            st.write(f"Company Health: **{data['f_score']:.2f}**")
            st.write(f"Market Sentiment: **{data['smart_money_score']:.2f}**")
            st.write(f"Market Risk: **{data['risk_score']:.2f}**")
    else:
        st.info("Tap a Ticker to see the Investment Plan.")
