import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Insight Pro", layout="wide", initial_sidebar_state="expanded")

# 2. THE "NO-GHOST" CSS ENGINE (Forces visibility on all elements)
st.markdown("""
    <style>
        /* 1. FORCE GLOBAL VISIBILITY */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
            color: #202124 !important;
        }

        /* 2. REMOVE HEADER/TOOLBAR */
        header, [data-testid="stToolbar"], [data-testid="stDecoration"] { 
            display: none !important; 
        }

        /* 3. FIX DROPDOWNS (Sector Filter) */
        div[data-baseweb="select"] * {
            color: #202124 !important;
            fill: #202124 !important;
        }
        div[role="listbox"] div {
            color: #202124 !important;
            background-color: #FFFFFF !important;
        }

        /* 4. FIX POPUP (History Dialog) */
        div[role="dialog"], div[role="dialog"] * {
            color: #202124 !important;
            background-color: #FFFFFF !important;
        }
        /* Style the table inside the popup specifically */
        div[role="dialog"] table { color: #202124 !important; }
        div[role="dialog"] thead tr th { background-color: #F1F3F4 !important; color: #202124 !important; }

        /* 5. FIX CONVICTION LABELS */
        .intel-label { 
            font-weight: 800 !important; 
            color: #202124 !important; 
            display: block; 
            margin-top: 12px;
            font-size: 14px !important;
        }

        /* 6. METRIC CONTRAST */
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; }
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }

        /* 7. SIDEBAR VISIBILITY */
        [data-testid="stSidebar"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
            background-color: #F8F9FA !important;
            color: #202124 !important;
        }

        /* 8. ACTION BUTTON */
        div.stButton > button {
            background-color: #1A73E8 !important;
            color: #FFFFFF !important;
            border-radius: 4px !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 10px 20px !important;
        }
        div.stButton > button:hover { background-color: #1557B0 !important; }
        div.stButton > button p { color: #FFFFFF !important; }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary
with st.sidebar:
    st.markdown("### 📑 Field Dictionary")
    st.markdown("""
    <div style="background:white; border:1px solid #DADCE0; padding:10px; border-radius:4px;">
    <p style="color:#202124; font-size:12px;">
    <b>Conviction</b>: 🎯 0.0 - 1.0<br>
    <b>Safety</b>: 🛡️ 0.0 - 1.0<br>
    <b>Health</b>: 💎 0.0 - 1.0<br>
    <b>Smart Money</b>: 🏛️ 0.0 - 1.0<br>
    <b>Beta</b>: 📈 0.0 - 3.0<br>
    <b>Kelly</b>: 🔢 0% - 100%
    </p>
    </div>
    """, unsafe_allow_html=True)

# 4. Data Logic
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
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    return df, pivot[['symbol', 'sector'] + sorted(recent)]

raw_df, pivot_5_df = load_data()

# 5. Fixed History Dialog (Popup)
@st.dialog("Signal Change Audit", width="large")
def show_audit(symbol):
    st.markdown(f"<h2 style='color:#202124;'>Transition Audit: {symbol}</h2>", unsafe_allow_html=True)
    data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=True)
    data['changed'] = data['signal'] != data['signal'].shift(1)
    changes = data[data['changed'] == True].sort_values('asatdate', ascending=False)
    
    # Using a simple dataframe display which inherits the forced black text CSS
    st.dataframe(changes[['asatdate', 'signal', 'action', 'notes']].rename(columns={'asatdate': 'Date'}), use_container_width=True)

# 6. Global Navigation bar
m1, m2, m3, m4 = st.columns(4)
with m1: search = st.text_input("🔍 Search", value="", placeholder="Ticker...").upper()
with m2: sector = st.selectbox("📁 Sector", options=["All"] + sorted(pivot_5_df['sector'].unique().tolist()))
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with m4: st.metric("Current Regime", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

# 7. Main Dashboard Split
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
        gb.configure_column(c, cellStyle=js_style, width=110)
    
    gb.configure_selection(selection_mode="single")
    grid_out = AgGrid(filtered, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, allow_unsafe_jscode=True, theme="alpine", height=600)

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        # Action Bar
        c_head, c_btn = st.columns([1.5, 1])
        with c_head: st.markdown(f"<h2 style='color:#202124;'>{ticker} Intel</h2>", unsafe_allow_html=True)
        with c_btn: 
            if st.button("📊 AUDIT HISTORY"): show_audit(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Select Date Log", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # Intelligence Grid (Forced High Visibility)
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
        intel_row("Product Pipeline", d['pipeline_score'])

        st.markdown("#### 💰 Capital Strategy")
        st.success(f"Port Weight: **{d['final_weight']:.2%}\n** | Cash: **${d['final_dollars']:,}**")
        st.caption(f"Kelly Edge: {d['kelly_fraction']:.2%} | Beta: {d['beta']:.2f}")
    else:
        st.info("👈 Select a Ticker in the Matrix to view details.")
