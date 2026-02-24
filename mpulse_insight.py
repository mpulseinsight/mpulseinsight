import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration (Must be the very first Streamlit command)
st.set_page_config(page_title="mPulse Pro v3.1", layout="wide", initial_sidebar_state="expanded")

# 2. Hardened CSS 
# Added a fix to ensure that if an error occurs, it is still visible.
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
            color: #202124 !important;
        }
        /* Only hide decoration if the app actually loads */
        [data-testid="stHeader"] { background-color: rgba(255,255,255,0) !important; }
        .block-container { padding-top: 1rem !important; }
        
        /* Metric Styling */
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; }
        
        /* AgGrid Header Fix */
        .ag-header-cell-label { color: #202124 !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# 3. Data Engine
def get_db_connection():
    try:
        if "postgres" not in st.secrets:
            st.error("Missing 'postgres' section in Streamlit Secrets.")
            return None
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require",
            connect_timeout=10
        )
    except Exception as e:
        st.error(f"Database Connection Failed: {e}")
        return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        # Pulling all columns including the new audit/60d columns
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
    except Exception as e:
        st.error(f"Query Failed: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Formatting and Safe Pivot
    df['date_str'] = df['asatdate'].astype(str)
    
    # We pivot on 'execution_stance' to show the strategy in the grid
    pivot_col = 'execution_stance' if 'execution_stance' in df.columns else 'signal'
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                           values=pivot_col, aggfunc='first').reset_index().fillna('')
    
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent_dates = sorted(cols, reverse=True)[:5]
    return df, pivot[['symbol', 'sector'] + sorted(recent_dates)]

# --- LOAD DATA ---
with st.spinner("Synchronizing with Market Intelligence..."):
    raw_df, pivot_5_df = load_data()

# EMERGENCY CHECK: If data is missing, show a clear message and stop
if raw_df.empty:
    st.warning("⚠️ No data found in the database. Please ensure the JS pipeline has run.")
    st.info("Check your 'mpulse_execution_results' table in Postgres.")
    st.stop()

# 4. Sidebar Dictionary
with st.sidebar:
    st.markdown("### 📖 Strategy Key")
    st.info("**CORE_LONG**: Daily & 60D Aligned\n\n**STRUCTURAL**: 60D Trend Leader\n\n**TACTICAL**: Short-term Momentum")

# 5. Dashboard Layout
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Ticker Search").upper()
with m2: 
    sec_list = ["All Sectors"] + sorted(raw_df['sector'].unique().tolist())
    selected_sector = st.selectbox("📁 Sector Filter", options=sec_list)
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}")
with m4: st.metric("Regime", f"{raw_df['final_regime'].iloc[-1]}")

# 6. Grid & Intel Panel
col_grid, col_intel = st.columns([1.5, 1.5])

# Filtering
filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if selected_sector != "All Sectors": filtered = filtered[filtered['sector'] == selected_sector]

with col_grid:
    st.subheader("Matrix: Execution Stance")
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", width=100)
    
    # Color logic for the matrix
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
            gb.configure_column(c, cellStyle=js_style)
    
    gb.configure_selection(selection_mode="single")
    grid_response = AgGrid(filtered, gridOptions=gb.build(), allow_unsafe_jscode=True, 
                           update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine", height=500)

with col_intel:
    selected = grid_response.get('selected_rows')
    if selected is not None and len(selected) > 0:
        # Compatibility fix for different st-aggrid versions
        row = selected.iloc[0] if isinstance(selected, pd.DataFrame) else selected[0]
        ticker = row['symbol']
        
        # Get latest data for this ticker
        d = raw_df[raw_df['symbol'] == ticker].iloc[-1]
        
        st.header(f"{ticker} Intelligence")
        
        # --- TOP LEVEL ACTION ---
        st.success(f"**Recommended Action:** {d['suggested_action']} ({d['execution_stance']})")
        
        # --- DUAL HORIZON DISPLAY ---
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**⚡ Daily Tactical**")
            st.write(f"Signal: {d['signal']}")
            st.progress(min(max(float(d['s_hybrid']), 0.0), 1.0))
        with c2:
            st.markdown("**🛡️ 60-Day Structural**")
            st.write(f"Signal: {d['signal_60d']}")
            st.progress(min(max(float(d.get('s_structural', 0)), 0.0), 1.0))

        # --- AUDIT TRAIL ---
        with st.expander("🔍 View Allocation Math"):
            st.write(f"Confidence (Kelly): {d.get('kelly_fraction', 0):.1%}")
            st.write(f"Volatility Adj (Beta): {d.get('vol_scale', 1.0):.2f}x")
            st.write(f"Sector Strength: {d.get('sector_strength', 0):.1%}")
            st.write(f"**Final Weight: {d['final_weight']:.2%}**")
    else:
        st.info("Select a ticker from the matrix to view deep intelligence.")
