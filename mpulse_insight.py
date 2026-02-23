import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Material Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Google Material Design System (High Contrast & Colorful)
st.markdown("""
    <style>
        /* Base Page - Clean Grey/White */
        .block-container { padding-top: 1.5rem; background-color: #F8F9FA; }
        header { visibility: hidden; }
        
        /* Sidebar - Explicit Black Text */
        [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #DADCE0; }
        [data-testid="stSidebar"] * { color: #202124 !important; }
        
        /* The Card Look - White with soft shadows */
        div[data-testid="column"] { 
            background-color: #FFFFFF; border: 1px solid #DADCE0; 
            padding: 20px; border-radius: 8px; 
            box-shadow: 0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15);
            margin-bottom: 15px;
        }

        /* Metrics - High Contrast Blue */
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; font-size: 13px !important; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }

        /* BUTTON FIX: Google Blue with White Text */
        div.stButton > button {
            background-color: #1A73E8 !important;
            color: #FFFFFF !important;
            border-radius: 4px !important;
            font-weight: 700 !important;
            border: none !important;
            width: 100%;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover { background-color: #1765C1 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important; }

        /* Dictionary Table Styling */
        .dict-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .dict-table td { border: 1px solid #F1F3F4; padding: 10px 5px; font-size: 13px; color: #202124 !important; }
        .dict-header { background-color: #F1F3F4; font-weight: 700; color: #5F6368 !important; }

        /* Intelligence Progress Bars Customization */
        .stProgress > div > div > div > div { background-image: linear-gradient(to right, #D93025, #FBBC04, #1E8E3E); }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary (Structured Table)
with st.sidebar:
    st.image("https://www.gstatic.com/images/branding/product/2x/analytics_64dp.png", width=40)
    st.title("Data Dictionary")
    st.markdown("""
    <table class="dict-table">
        <tr class="dict-header"><td>Metric</td><td>Meaning</td><td>Range</td></tr>
        <tr><td><b>Conviction</b></td><td>Master Signal Score</td><td>🎯 0 - 1.0</td></tr>
        <tr><td><b>Safety</b></td><td>Volatility Shield</td><td>🛡️ 0 - 1.0</td></tr>
        <tr><td><b>Health</b></td><td>Biz Fundamental Quality</td><td>💎 0 - 1.0</td></tr>
        <tr><td><b>Port. %</b></td><td>Money to Invest</td><td>💰 0 - 100%</td></tr>
        <tr><td><b>GV Mix</b></td><td>Growth/Value Balance</td><td>⚖️ 0 - 1.0</td></tr>
        <tr><td><b>Institutional</b></td><td>Smart Money Flow</td><td>🏛️ 0 - 1.0</td></tr>
        <tr><td><b>Beta</b></td><td>Sensitivity to Market</td><td>📈 0 - 3.0</td></tr>
        <tr><td><b>Kelly</b></td><td>Mathematical Edge</td><td>🔢 0 - 100%</td></tr>
    </table>
    """, unsafe_allow_html=True)

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
    
    # Standard Pivot
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    
    # 5-Date Slice for UI Matrix
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent_dates = sorted(cols, reverse=True)[:5]
    pivot_display = pivot[['symbol', 'sector'] + sorted(recent_dates)]
    
    return df, pivot_display

raw_df, pivot_5_df = load_data()

# 5. History Audit Dialog
@st.dialog("Signal Transition Audit", width="large")
def show_audit(symbol):
    st.subheader(f"Historical Audit: {symbol}")
    data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=True)
    data['changed'] = data['signal'] != data['signal'].shift(1)
    changes = data[data['changed'] == True].sort_values('asatdate', ascending=False)
    st.dataframe(changes[['asatdate', 'signal', 'action', 'notes']], use_container_width=True)

# 6. Global Header
h1, h2, h3, h4 = st.columns(4)
with h1: search = st.text_input("🔍 Search Ticker", "").upper()
with h2: sector = st.selectbox("📁 Sector", ["All"] + sorted(pivot_5_df['sector'].unique().tolist()))
with h3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with h4: st.metric("Market Regime", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

# 7. Main Grid Layout
col_mat, col_intel = st.columns([1.6, 1.4])

filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_mat:
    st.markdown("### 🗓️ Signal Matrix (Recent)")
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", width=100)
    
    # Colorful Heatmap (Google Palette)
    cell_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: '800', border: '1px solid #CEEAD6'};
        if (v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: '800', border: '1px solid #FAD2CF'};
        return {backgroundColor: '#F8F9FA', color: '#3C4043', border: '1px solid #DADCE0'};
    }
    """)
    for c in [x for x in filtered.columns if x not in ['symbol', 'sector']]:
        gb.configure_column(c, cellStyle=cell_style, width=110)
    
    gb.configure_selection(selection_mode="single")
    grid_response = AgGrid(filtered, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=650)

with col_intel:
    sel = grid_response.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        # Header with Colorful Button
        c_name, c_btn = st.columns([1.5, 1])
        with c_name: st.markdown(f"## {ticker} Intel")
        with c_btn: 
            if st.button("📊 VIEW FULL HISTORY"):
                show_audit(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Historical Date", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # Intelligence Grid with Progress Bars (The "Colorful/Meaningful" Part)
        def intel_block(label, val, max_val=1.0):
            st.write(f"**{label}**: `{val:.4f}`")
            # Normalize for progress bar
            st.progress(min(max(val / max_val, 0.0), 1.0))

        st.markdown("#### 🎯 Conviction Metrics")
        intel_block("Conviction (Hybrid)", d['s_hybrid'])
        intel_block("Safety Buffer", (1 - d['risk_score']))
        intel_block("Financial Strength", d['f_score'])
        
        st.markdown("#### 🏛️ Market & Sentiment")
        intel_block("Professional Buying", d['smart_money_score'])
        intel_block("Wall St. Consensus", d['analyst_score'])
        intel_block("Product Pipeline", d['pipeline_score'])

        st.markdown("#### 💰 Execution Strategy")
        st.info(f"Recommended Weight: **{d['final_weight']:.2%}** | Cash Needed: **${d['final_dollars']:,}**")
        st.caption(f"Kelly Edge: {d['kelly_fraction']:.2%} | Beta: {d['beta']:.2f}")

    else:
        st.warning("Please click a Ticker in the Matrix to load the Intelligence Grid.")
