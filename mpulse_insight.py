import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="expanded")

# 2. Google Classic High-Contrast CSS
st.markdown("""
    <style>
        /* Overall Page Contrast */
        .block-container { padding-top: 1.5rem; background-color: #FFFFFF; color: #202124; }
        header { visibility: hidden; }
        
        /* Sidebar Contrast */
        [data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #DADCE0; }
        
        /* High-Contrast Content Containers */
        div[data-testid="column"] { 
            background-color: #FFFFFF; 
            border: 1px solid #BDC1C6; 
            padding: 20px; 
            border-radius: 4px; 
            margin-bottom: 15px;
        }
        
        /* Global Text Overrides - Fixing Visibility */
        p, span, label, h1, h2, h3 { color: #202124 !important; font-family: 'Roboto', Arial, sans-serif; }
        
        /* Top Metrics Visibility (Fixing 'White Buckets') */
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; font-size: 13px !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; font-size: 28px !important; }
        
        /* Intelligence Grid Styling */
        .grid-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #F1F3F4; }
        .grid-label { color: #3C4043; font-weight: 500; font-size: 14px; }
        .grid-value { color: #1A73E8; font-weight: 700; font-size: 14px; }
        .grid-header { background-color: #F1F3F4; padding: 8px; font-weight: 700; font-size: 12px; color: #5F6368; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar: Meaning of Fields (Left Side)
with st.sidebar:
    st.markdown("### 🔍 Field Definitions")
    st.markdown("""
    ---
    **Market Fear (VIX)**
    *Range: 10 - 80* | Fear index.
    
    **Current Regime**
    *Range: RISK_ON / OFF* | Trend mode.
    
    **Conviction (Hybrid)**
    *Range: 0.0 - 1.0* | Master score.
    
    **Safety Buffer**
    *Range: 0.0 - 1.0* | Resilience.
    
    **Financial Strength**
    *Range: 0.0 - 1.0* | F-Score quality.
    
    **Portfolio Share**
    *Range: 0% - 100%* | Capital weight.
    
    **Cash Required**
    *Range: $ Value* | Trade amount.
    
    **Growth/Value Mix**
    *Range: 0.0 - 1.0* | Valuation health.
    
    **Product Pipeline**
    *Range: 0.0 - 1.0* | Future catalysts.
    
    **Professional Buying**
    *Range: 0.0 - 1.0* | Institutional flow.
    
    **Wall St. Consensus**
    *Range: 0.0 - 1.0* | Analyst ratings.
    
    **Stock Beta**
    *Range: 0.0 - 3.0* | Market sensitivity.
    
    **Volatility Scaling**
    *Range: 0.0 - 2.0* | Size adjustment.
    
    **Kelly Edge**
    *Range: 0% - 100%* | Optimal bet size.
    
    **Sector Exposure**
    *Range: 0% - 100%* | Industry risk.
    """)

# 4. Database Integration
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except Exception as e:
        st.error("Connection Failed. Check Secrets.")
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

# 5. Top Metrics Bar
m1, m2, m3, m4 = st.columns(4)
with m1:
    v_val = raw_df['vix'].iloc[-1] if not raw_df.empty else 0
    st.metric("Market Fear Index", f"{v_val:.2f}")
with m2:
    r_val = raw_df['final_regime'].iloc[-1] if not raw_df.empty else "N/A"
    st.metric("Current Regime", r_val)
with m3:
    st.text_input("🔍 Search", key="search_box", placeholder="Ticker...").upper()
with m4:
    sector_list = ["All Sectors"] + sorted(pivot_df['sector'].unique().tolist())
    st.selectbox("📁 Sector", options=sector_list, key="sector_box")

# 6. Content Split
col_matrix, col_grid = st.columns([1.7, 1.3])

# Filtering
f_pivot = pivot_df.copy()
if st.session_state.search_box:
    f_pivot = f_pivot[f_pivot['symbol'].str.contains(st.session_state.search_box)]
if st.session_state.sector_box != "All Sectors":
    f_pivot = f_pivot[f_pivot['sector'] == st.session_state.sector_box]

with col_matrix:
    st.subheader("Signal Matrix")
    gb = GridOptionsBuilder.from_dataframe(f_pivot)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=100)
    gb.configure_column("sector", pinned="left", headerName="Sector", width=130)
    
    # High-Contrast Cell Styling
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold', border: '1px solid #CEEAD6'};
        if (val.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold', border: '1px solid #FAD2CF'};
        return {backgroundColor: '#F8F9FA', color: '#3C4043', border: '1px solid #DADCE0'};
    }
    """)
    
    for c in [col for col in f_pivot.columns if col not in ['symbol', 'sector']]:
        gb.configure_column(c, cellStyle=signal_style, width=110)

    gb.configure_selection(selection_mode="single")
    gb.configure_grid_options(headerHeight=40, rowHeight=38)
    
    grid_response = AgGrid(f_pivot, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=750)

with col_grid:
    # Handle Selection
    selected = grid_response.get('selected_rows')
    has_row = False
    if selected is not None:
        if isinstance(selected, pd.DataFrame) and not selected.empty:
            has_row, sel_row = True, selected.iloc[0]
        elif isinstance(selected, list) and len(selected) > 0:
            has_row, sel_row = True, selected[0]

    if has_row:
        ticker = sel_row['symbol']
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        st.markdown(f"## {ticker} Intelligence Grid")
        date_pick = st.selectbox("Historical Date Selection", options=hist['date_str'].tolist())
        d = hist[hist['date_str'] == date_pick].iloc[0]

        # Intelligence Grid (The 15 Requested Fields)
        def draw_row(label, val):
            st.markdown(f'<div class="grid-row"><span class="grid-label">{label}</span><span class="grid-value">{val}</span></div>', unsafe_allow_html=True)

        st.markdown('<div class="grid-header">PRIMARY SCORECARD</div>', unsafe_allow_html=True)
        draw_row("Conviction (Hybrid)", f"{d['s_hybrid']:.4f}")
        draw_row("Safety Buffer", f"{(1-d['risk_score']):.4f}")
        draw_row("Financial Strength (F-Score)", f"{d['f_score']:.4f}")
        
        st.markdown('<div class="grid-header">TRADE EXECUTION</div>', unsafe_allow_html=True)
        draw_row("Portfolio Share", f"{d['final_weight']:.2%}")
        draw_row("Cash Required", f"${d['final_dollars']:,}")
        draw_row("Kelly Edge", f"{d['kelly_fraction']:.2%}")

        st.markdown('<div class="grid-header">ANALYSIS & FLOW</div>', unsafe_allow_html=True)
        draw_row("Growth/Value Mix", f"{d['gv_score']:.4f}")
        draw_row("Product Pipeline", f"{d['pipeline_score']:.4f}")
        draw_row("Professional Buying", f"{d['smart_money_score']:.4f}")
        draw_row("Wall St. Consensus", f"{d['analyst_score']:.4f}")

        st.markdown('<div class="grid-header">RISK DYNAMICS</div>', unsafe_allow_html=True)
        draw_row("Stock Beta", f"{d['beta']:.2f}")
        draw_row("Volatility Scaling", f"{d['vol_scale']:.2f}")
        draw_row("Sector Exposure", f"{d['sector_weight']:.2%}")
        
    else:
        st.info("👈 Select a Ticker to display Intelligence Grid.")
