import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight Pro", layout="wide", initial_sidebar_state="expanded")

# 2. ULTRA-CONTRAST CSS (Forces everything to Black/Blue)
st.markdown("""
    <style>
        /* Force background to White and Text to Black */
        .main, .block-container { background-color: #FFFFFF !important; color: #202124 !important; }
        
        /* Force Sidebar text to Black */
        [data-testid="stSidebar"], [data-testid="stSidebar"] * { 
            background-color: #F8F9FA !important; 
            color: #202124 !important; 
        }

        /* Force ALL Markdown, Labels, and Paragraphs to Deep Black */
        p, span, label, div, h1, h2, h3, h4, h5, h6 { 
            color: #202124 !important; 
            font-family: 'Roboto', sans-serif !important; 
        }

        /* High-Contrast Cards */
        div[data-testid="column"] { 
            background-color: #FFFFFF !important; 
            border: 1px solid #DADCE0 !important; 
            padding: 15px; 
            border-radius: 8px; 
            box-shadow: 0 1px 3px rgba(60,64,67,0.15);
            margin-bottom: 15px;
        }

        /* Force Metrics to Blue/Grey */
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }

        /* BUTTON FIX: Google Blue with White Text (Mandatory) */
        div.stButton > button {
            background-color: #1A73E8 !important;
            color: #FFFFFF !important;
            border-radius: 4px !important;
            font-weight: 700 !important;
            border: none !important;
            text-transform: uppercase;
            padding: 10px;
        }
        div.stButton > button p { color: #FFFFFF !important; } /* Fix for button text */

        /* Progress Bar Labeling Color */
        .intel-label { 
            font-weight: 700 !important; 
            color: #202124 !important; 
            margin-bottom: 2px;
            display: block;
        }

        /* Dictionary Table */
        .dict-table { width: 100%; border-collapse: collapse; background: white; }
        .dict-table td { border: 1px solid #DADCE0; padding: 8px; font-size: 13px; color: #202124 !important; }
        .dict-head { background-color: #F1F3F4; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary
with st.sidebar:
    st.markdown("### 📑 Data Dictionary")
    st.markdown("""
    <table class="dict-table">
        <tr class="dict-head"><td>Field</td><td>Range</td><td>Icon</td></tr>
        <tr><td>Market Fear</td><td>10 - 80</td><td>📉</td></tr>
        <tr><td>Regime</td><td>ON / OFF</td><td>🔄</td></tr>
        <tr><td>Conviction</td><td>0.0 - 1.0</td><td>🎯</td></tr>
        <tr><td>Safety</td><td>0.0 - 1.0</td><td>🛡️</td></tr>
        <tr><td>Health</td><td>0.0 - 1.0</td><td>💎</td></tr>
        <tr><td>Port. Share</td><td>0% - 100%</td><td>💰</td></tr>
        <tr><td>Smart Money</td><td>0.0 - 1.0</td><td>🏛️</td></tr>
        <tr><td>Beta</td><td>0.0 - 3.0</td><td>📈</td></tr>
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
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index().fillna('')
    # Limit to 5 dates
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    return df, pivot[['symbol', 'sector'] + sorted(recent)]

raw_df, pivot_5_df = load_data()

# 5. History Audit (Popup)
@st.dialog("Detailed Signal History", width="large")
def show_audit(symbol):
    st.markdown(f"### Audit Trail: {symbol}")
    data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=True)
    data['changed'] = data['signal'] != data['signal'].shift(1)
    changes = data[data['changed'] == True].sort_values('asatdate', ascending=False)
    st.table(changes[['asatdate', 'signal', 'action', 'notes']])

# 6. Navigation
m1, m2, m3, m4 = st.columns(4)
with m1: search = st.text_input("🔍 Search", "").upper()
with m2: sector = st.selectbox("📁 Sector", ["All"] + sorted(pivot_5_df['sector'].unique().tolist()))
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with m4: st.metric("Market Regime", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

# 7. Main Grid
col_grid, col_intel = st.columns([1.6, 1.4])

filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    st.markdown("### 🗓️ Signal Matrix (Recent)")
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
    grid_out = AgGrid(filtered, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=600)

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        # Action Bar
        c_head, c_btn = st.columns([1.5, 1])
        with c_head: st.markdown(f"## {ticker} Analysis")
        with c_btn: 
            if st.button("📊 AUDIT HISTORY"): show_audit(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Select Date", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # Intelligence Grid (Forcing Black Text Labels)
        def intel_row(label, val):
            st.markdown(f'<span class="intel-label">{label}: {val:.4f}</span>', unsafe_allow_html=True)
            st.progress(min(max(val, 0.0), 1.0))

        st.markdown("#### 🎯 Conviction Metrics")
        intel_row("Master Conviction", d['s_hybrid'])
        intel_row("Safety Buffer", (1 - d['risk_score']))
        intel_row("Business Health", d['f_score'])
        
        st.markdown("#### 🏛️ Sentiment & Flow")
        intel_row("Smart Money Flow", d['smart_money_score'])
        intel_row("Analyst Sentiment", d['analyst_score'])
        intel_row("Product Pipeline", d['pipeline_score'])

        st.markdown("#### 💰 Strategy")
        st.success(f"Port Weight: **{d['final_weight']:.2%}\n** | Cash: **${d['final_dollars']:,}**")
    else:
        st.warning("Please click a ticker in the matrix to load Intelligence Grid.")
