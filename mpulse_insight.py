import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight", layout="wide", initial_sidebar_state="expanded")

# 2. Google-Standard Classic CSS (High Contrast)
st.markdown("""
    <style>
        /* Main page settings */
        .block-container { padding-top: 1.5rem; background-color: #F8F9FA; color: #202124; }
        header { visibility: hidden; }
        
        /* High Contrast Card Styling */
        div[data-testid="column"] { 
            background-color: #FFFFFF; 
            border: 1px solid #DADCE0; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15);
            margin-bottom: 15px;
        }
        
        /* Force Metric Text Visibility (Fixing the 'White Bucket' issue) */
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; font-size: 14px !important; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }
        [data-testid="stMetricDelta"] { font-weight: 700 !important; }

        /* Typography */
        h1, h2, h3, p, span { font-family: 'Roboto', 'Arial', sans-serif; color: #202124 !important; }
        
        /* Table / Matrix Styling */
        .ag-theme-alpine { --ag-header-background-color: #F1F3F4; --ag-border-color: #DADCE0; }
        
        /* Custom Intelligence Grid */
        .intel-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #F1F3F4; }
        .intel-label { color: #5F6368; font-weight: 600; font-size: 13px; }
        .intel-value { color: #202124; font-weight: 700; font-size: 14px; font-family: 'Courier New', monospace; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary (The Reference Desk)
with st.sidebar:
    st.title("📑 Data Dictionary")
    st.info("Hover over metrics for details. Below are the standard ranges for scoring:")
    st.markdown("""
    **Primary Scales (0.00 to 1.00)**
    * **0.60+ :** Strong / Positive 🟢
    * **0.40 - 0.59 :** Neutral / Hold 🟡
    * **0.00 - 0.39 :** Weak / Negative 🔴
    ---
    **Definitions:**
    * **Conviction:** Overall strength of the math.
    * **Safety:** Resistance to market volatility.
    * **Health:** Underlying business quality.
    * **Professional Flow:** Institutional buying activity.
    """)

# 4. Database Connection
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except Exception as e:
        st.error("❌ Database connection failed. Check your Streamlit Secrets.")
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

# 5. Top Navigation & Global Metrics
t1, t2, t3, t4 = st.columns(4)
with t1:
    search_q = st.text_input("🔍 Search Ticker", placeholder="e.g. MSFT").upper()
with t2:
    sector_list = ["All Sectors"] + sorted(pivot_df['sector'].unique().tolist())
    sel_sector = st.selectbox("📁 Sector Filter", options=sector_list)
with t3:
    vix = raw_df['vix'].iloc[-1] if not raw_df.empty else 0
    st.metric("Market Fear Index", f"{vix:.2f}", help="Volatility Index (VIX). Above 25 indicates panic.")
with t4:
    regime = raw_df['final_regime'].iloc[-1] if not raw_df.empty else "N/A"
    st.metric("Current Regime", regime, help="The overall market environment trend.")

# 6. Main Content
col_timeline, col_intel = st.columns([1.6, 1.4])

# Filter pivot
filtered_pivot = pivot_df.copy()
if search_q:
    filtered_pivot = filtered_pivot[filtered_pivot['symbol'].str.contains(search_q)]
if sel_sector != "All Sectors":
    filtered_pivot = filtered_pivot[filtered_pivot['sector'] == sel_sector]

with col_timeline:
    st.subheader("Signal Timeline")
    gb = GridOptionsBuilder.from_dataframe(filtered_pivot)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=100)
    gb.configure_column("sector", pinned="left", headerName="Sector", width=140)
    
    # Classic Contrast Heatmap
    signal_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold', border: '1px solid #CEEAD6'};
        if (val.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold', border: '1px solid #FAD2CF'};
        if (val.includes('NEUTRAL')) return {backgroundColor: '#F8F9FA', color: '#3C4043', border: '1px solid #DADCE0'};
        return {};
    }
    """)
    
    date_cols = [c for c in filtered_pivot.columns if c not in ['symbol', 'sector']]
    for c in date_cols:
        gb.configure_column(c, cellStyle=signal_style, width=110)

    gb.configure_selection(selection_mode="single")
    gb.configure_grid_options(headerHeight=40, rowHeight=35)
    
    grid_response = AgGrid(filtered_pivot, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=750)

with col_intel:
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
        
        st.markdown(f"## {ticker} Analysis")
        date_pick = st.selectbox("Select Signal Date", options=hist['date_str'].tolist())
        data = hist[hist['date_str'] == date_pick].iloc[0]

        # Big Action Alert
        act_map = {"ENTER": ("#137333", "#E6F4EA"), "EXIT": ("#C5221F", "#FCE8E6"), "WAIT": ("#3C4043", "#F1F3F4")}
        txt_c, bg_c = act_map.get(data['action'], ("#3C4043", "#F1F3F4"))
        
        st.markdown(f"""
            <div style="background-color:{bg_c}; border: 2px solid {txt_c}; padding:15px; border-radius:8px; text-align:center;">
                <h2 style="margin:0; color:{txt_c} !important;">{data['action']}</h2>
                <p style="margin:0; font-weight:bold; color:{txt_c} !important;">{data['notes']}</p>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        # The Vertical Intelligence Grid (Every DB Field)
        st.markdown("### 📊 Decision Intelligence")
        
        def intel_row(label, value, tooltip):
            st.markdown(f"""
                <div class="intel-row" title="{tooltip}">
                    <span class="intel-label">{label}</span>
                    <span class="intel-value">{value}</span>
                </div>
            """, unsafe_allow_html=True)

        # Categorized Vertical Grid
        with st.container():
            st.write("**Core Conviction**")
            intel_row("Conviction (Hybrid)", f"{data['s_hybrid']:.4f}", "The master score driving the signal.")
            intel_row("Safety Buffer", f"{(1-data['risk_score']):.4f}", "How well the stock resists market drops.")
            intel_row("Portfolio Share", f"{data['final_weight']:.2%}", "Percentage of your total money to invest.")
            intel_row("Cash Required", f"${data['final_dollars']:,}", "Exact dollar amount to trade.")
            
            st.write("**Fundamental Health**")
            intel_row("Financial Strength", f"{data['f_score']:.4f}", "F-Score: Measures balance sheet quality.")
            intel_row("Growth/Value Mix", f"{data['gv_score']:.4f}", "Is the stock fairly priced for its growth?")
            intel_row("Product Pipeline", f"{data['pipeline_score']:.4f}", "Future revenue potential.")
            
            st.write("**Market Sentiment**")
            intel_row("Professional Buying", f"{data['smart_money_score']:.4f}", "Institutional 'Smart Money' flow.")
            intel_row("Wall St. Consensus", f"{data['analyst_score']:.4f}", "Average rating from investment banks.")
            
            st.write("**Risk & Scaling**")
            intel_row("Stock Beta", f"{data['beta']:.2f}", "Sensitivity to the general market (1.0 is average).")
            intel_row("Volatility Scaling", f"{data['vol_scale']:.2f}", "How the system adjusted for current volatility.")
            intel_row("Kelly Edge", f"{data['kelly_fraction']:.2%}", "The mathematical optimal bet size.")
            intel_row("Sector Exposure", f"{data['sector_weight']:.2%}", "How much of this sector you already own.")

    else:
        st.warning("Please click a row in the Timeline Matrix to view the Intel Grid.")
