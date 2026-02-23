import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="collapsed")

# 2. ULTRA-CONTRAST CSS (Space Optimization & Visibility)
st.markdown("""
    <style>
        /* REMOVE TOP SPACE & HEADERS */
        header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; background-color: #FFFFFF; }
        
        /* FORCE VISIBILITY */
        p, span, label, div, h1, h2, h3, h4, th, td { color: #202124 !important; font-family: 'Roboto', sans-serif !important; }
        
        /* FIX POPUP FONTS */
        div[role="dialog"], div[role="dialog"] * { color: #202124 !important; background-color: #FFFFFF !important; }
        .stTable td, .stTable th { color: #202124 !important; font-size: 14px !important; }

        /* MATERIAL CARDS */
        div[data-testid="column"] { 
            background-color: #FFFFFF !important; border: 1px solid #DADCE0 !important; 
            padding: 10px; border-radius: 4px; margin-bottom: 5px;
        }

        /* BUTTON FIX */
        div.stButton > button {
            background-color: #1A73E8 !important; color: #FFFFFF !important;
            border-radius: 4px !important; font-weight: 700 !important; width: 100%;
        }
        div.stButton > button p { color: #FFFFFF !important; }

        /* DROPDOWN FIX */
        div[data-baseweb="select"] * { color: #202124 !important; }

        /* INTEL LABELS */
        .intel-label { font-weight: 700 !important; color: #202124 !important; display: block; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary
with st.sidebar:
    st.markdown("### 📖 Reference")
    st.info("Scores range from 0.0 (Weak) to 1.0 (Strong).")
    st.markdown("""
    **Conviction**: Master Logic Score  
    **Safety**: Volatility Buffer  
    **Smart Money**: Institutional Flow  
    **Kelly**: Math Optimal Size
    """)

# 4. Data Engine
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"],
                                user=creds["user"], password=creds["password"], sslmode="require")
    except: return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
    df['date_str'] = df['asatdate'].astype(str)
    
    # Grid Pivot
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    return df, pivot[['symbol', 'sector'] + sorted(recent)]

raw_df, pivot_5_df = load_data()

# 5. FIXED History Dialog (Handles No Records Issue)
@st.dialog("Signal History Audit", width="large")
def show_audit(symbol):
    st.markdown(f"<h3 style='color:#202124;'>Historical Log: {symbol}</h3>", unsafe_allow_html=True)
    # Pull last 15 records regardless of change to ensure data is seen
    data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=False).head(15)
    
    if data.empty:
        st.error("No historical records found for this ticker.")
    else:
        # Style the dataframe for maximum readability
        st.dataframe(
            data[['asatdate', 'signal', 'action', 'notes']].rename(columns={'asatdate': 'Date'}),
            use_container_width=True,
            hide_index=True
        )

# 6. Optimized Top Navigation (Leveraging Space)
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Ticker", placeholder="Search...").upper()
with m2: sector = st.selectbox("📁 Sector", options=["All"] + sorted(pivot_5_df['sector'].unique().tolist()))
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with m4: st.metric("Regime", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

# 7. Main Dashboard Split
col_grid, col_intel = st.columns([1.6, 1.4])

filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    st.markdown("### 🗓️ Signal Matrix")
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", width=90)
    
    js_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
        return {backgroundColor: '#F8F9FA', color: '#3C4043'};
    }
    """)
    for c in [x for x in filtered.columns if x not in ['symbol', 'sector']]:
        gb.configure_column(c, cellStyle=js_style, width=105)
    
    gb.configure_selection(selection_mode="single")
    
    # 20 Records Displayed with Scrolling Enabled
    grid_out = AgGrid(
        filtered, 
        gridOptions=gb.build(), 
        update_mode=GridUpdateMode.SELECTION_CHANGED, 
        allow_unsafe_jscode=True, 
        theme="alpine", 
        height=650, # Height adjusted to fit roughly 20 records
        fit_columns_on_grid_load=True
    )

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        # Space-Efficient Header
        c_head, c_btn = st.columns([1.5, 1])
        with c_head: st.markdown(f"<h2 style='margin:0;'>{ticker} Intel</h2>", unsafe_allow_html=True)
        with c_btn: 
            if st.button("📊 AUDIT HISTORY"): show_audit(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Date Log", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # Intelligence Grid (Ultra-Contrast Labels)
        def intel_row(label, val):
            st.markdown(f'<span class="intel-label">{label}: <b style="color:#1A73E8;">{val:.4f}</b></span>', unsafe_allow_html=True)
            st.progress(min(max(val, 0.0), 1.0))

        st.markdown("#### 🎯 Conviction Scorecard")
        intel_row("Master Conviction", d['s_hybrid'])
        intel_row("Safety Buffer", (1 - d['risk_score']))
        intel_row("Business Health", d['f_score'])
        
        st.markdown("#### 🏛️ Sentiment & Flow")
        intel_row("Institutional Flow", d['smart_money_score'])
        intel_row("Analyst Consensus", d['analyst_score'])

        st.markdown("#### 💰 Execution")
        st.success(f"Port Weight: **{d['final_weight']:.2%}** | Cash: **${d['final_dollars']:,}**")
    else:
        st.info("👈 Select a Ticker in the Matrix to view details.")
