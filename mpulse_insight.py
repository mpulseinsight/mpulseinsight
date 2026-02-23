import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration - Extreme High Density
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS to kill whitespace and head space
st.markdown("""
    <style>
        .block-container { padding-top: 0rem; padding-bottom: 0rem; max-width: 98%; }
        header { visibility: hidden; }
        #MainMenu { visibility: hidden; }
        div[data-testid="column"] { 
            background-color: #161b22; border: 1px solid #30363d; 
            padding: 10px; border-radius: 4px; 
        }
        .stMetric { padding: 2px !important; }
        .stSelectbox, .stTextInput { margin-bottom: -15px; }
        /* Shrink font size for the entire app slightly for density */
        html, body, [class*="ViewContainer"] { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# 2. Database Connection (Hardcoded)
# --- Updated Database Connection (leveraging Environment Variables) ---
@st.cache_resource
def get_db_connection():
    try:
        # Streamlit automatically maps 'st.secrets' to environment variables
        creds = st.secrets["postgres"]
        
        return psycopg2.connect(
            host=creds["host"],
            port=creds["port"],
            database=creds["database"],
            user=creds["user"],
            password=creds["password"],
            sslmode="require"
        )
    except Exception as e:
        st.error("❌ Database credentials not found or connection failed.")
        st.info("Check Streamlit Cloud Secrets or local .streamlit/secrets.toml")
        return None

@st.cache_data(ttl=60)
def load_full_data():
    conn = get_db_connection()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    query = "SELECT * FROM mpulse_execution_results WHERE asatdate >= CURRENT_DATE - INTERVAL '30 days' ORDER BY asatdate ASC"
    df = pd.read_sql(query, conn)
    df['date_str'] = df['asatdate'].astype(str)
    # Pivot for Timeline - Keeping Sector as an index so it stays in the row
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    return df, pivot

raw_df, pivot_df = load_full_data()

# --- 3. TOP FILTER BAR (Cleaned up) ---
t1, t2, t3 = st.columns([1, 1, 2])

with t1:
    search_symbol = st.text_input("🔍 Search Symbol", placeholder="e.g. AAPL").upper()

with t2:
    all_sectors = ["All Sectors"] + sorted(pivot_df['sector'].unique().tolist())
    selected_sector = st.selectbox("📁 Filter Sector", options=all_sectors)

# --- FILTER LOGIC ---
filtered_pivot = pivot_df.copy()
if search_symbol:
    filtered_pivot = filtered_pivot[filtered_pivot['symbol'].str.contains(search_symbol)]
if selected_sector != "All Sectors":
    filtered_pivot = filtered_pivot[filtered_pivot['sector'] == selected_sector]

# --- 4. MAIN UI ---
col_timeline, col_detail = st.columns([2.2, 0.8])

with col_timeline:
    gb = GridOptionsBuilder.from_dataframe(filtered_pivot)
    
    # Grid Layout: Pin Symbol and Sector to the left for easy reading
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=90, sort='asc')
    gb.configure_column("sector", pinned="left", headerName="Sector", width=140)
    
    # Heatmap style for signal cells
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#064e3b', color: '#ecfdf5', fontSize: '11px', borderRight: '1px solid #30363d'};
        if (val.includes('BEARISH')) return {backgroundColor: '#7f1d1d', color: '#fef2f2', fontSize: '11px', borderRight: '1px solid #30363d'};
        if (val.includes('NEUTRAL')) return {backgroundColor: '#1e293b', color: '#f1f5f9', fontSize: '11px', borderRight: '1px solid #30363d'};
        return {fontSize: '11px', borderRight: '1px solid #30363d'};
    }
    """)

    # Apply style to date columns
    date_cols = [col for col in filtered_pivot.columns if col not in ['sector', 'symbol']]
    for c in date_cols:
        gb.configure_column(c, cellStyle=signal_style, width=100)

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(headerHeight=30, rowHeight=28) # Shorter rows for density
    
    grid_response = AgGrid(
        filtered_pivot, 
        gridOptions=gb.build(), 
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True, 
        theme="alpine", 
        height=750
    )

with col_detail:
    selected_rows = grid_response.get('selected_rows')
    
    # Selection Logic
    has_selection = False
    if selected_rows is not None:
        if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
            has_selection, sel_row = True, selected_rows.iloc[0]
        elif len(selected_rows) > 0:
            has_selection, sel_row = True, selected_rows[0]

    if has_selection:
        ticker = sel_row['symbol']
        ticker_history = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        
        st.write(f"### {ticker}")
        st.write(f"*{sel_row['sector']}*")
        
        selected_date = st.selectbox("Analysis Date", options=ticker_history['date_str'].tolist(), label_visibility="collapsed")
        data = ticker_history[ticker_history['date_str'] == selected_date].iloc[0]

        # Compact Action Card
        if data['action'] in ['ENTER', 'ACCUMULATE']:
            st.success(f"**{data['action']}**")
        elif data['action'] == 'EXIT':
            st.error(f"**{data['action']}**")
        else:
            st.warning(f"**{data['action']}**")
        
        # Metrics Display
        m1, m2 = st.columns(2)
        m1.metric("Hybrid", f"{data['s_hybrid']:.2f}")
        m2.metric("Kelly", f"{data['kelly_fraction']:.1%}")
        
        m3, m4 = st.columns(2)
        m3.metric("Weight", f"{data['final_weight']:.1%}")
        m4.metric("Value", f"${data['final_dollars']:,}")

        with st.expander("Diagnostics", expanded=True):
            st.write(f"Fundamental: `{data['f_score']:.2f}`")
            st.write(f"Smart Money: `{data['smart_money_score']:.2f}`")
            st.write(f"Analyst: `{data['analyst_score']:.2f}`")
            st.write(f"Risk: `{data['risk_score']:.2f}`")

        with st.expander("Market Context"):
            st.write(f"Regime: **{data['final_regime']}**")
            st.write(f"VIX: {data['vix']} | Beta: {data['beta']}")
    else:
        st.write("Click a ticker row to inspect signal logic.")
