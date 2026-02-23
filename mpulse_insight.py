import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. HARDENED CSS (Forcing Black Text and Zero Margins)
st.markdown("""
    <style>
        /* Force Global Font Visibility */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
        }
        
        /* Remove Top Header */
        header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0rem !important; margin-top: -20px; }

        /* Force Sidebar Text Visibility */
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #DADCE0; }
        [data-testid="stSidebar"] * { color: #202124 !important; }

        /* Force Dropdown Visibility (Fixes the 'Blank' Font Issue) */
        div[data-baseweb="select"] * { color: #202124 !important; font-weight: 600 !important; }
        div[role="listbox"] * { color: #202124 !important; background-color: #FFFFFF !important; }

        /* Force Dialog/Popup Visibility */
        div[role="dialog"] { background-color: #FFFFFF !important; color: #202124 !important; border: 1px solid #DADCE0; }
        div[role="dialog"] * { color: #202124 !important; }

        /* Metric Contrast */
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; }

        /* Button Hardening */
        div.stButton > button {
            background-color: #1A73E8 !important; color: #FFFFFF !important;
            border-radius: 4px !important; font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary (Hardened with Inline Styles)
with st.sidebar:
    st.markdown('<h2 style="color:#202124; margin-bottom:5px;">📖 Dictionary</h2>', unsafe_allow_html=True)
    dict_html = """
    <div style="background-color:#FFFFFF; border:1px solid #DADCE0; padding:10px; border-radius:5px;">
        <table style="width:100%; border-collapse:collapse; color:#202124;">
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🎯 <b>Conviction</b></td><td style="text-align:right;">0.0 - 1.0</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🛡️ <b>Safety</b></td><td style="text-align:right;">0.0 - 1.0</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>💎 <b>Health</b></td><td style="text-align:right;">0.0 - 1.0</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🏛️ <b>Institutional</b></td><td style="text-align:right;">0.0 - 1.0</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>📈 <b>Beta</b></td><td style="text-align:right;">0.0 - 3.0</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🔢 <b>Kelly</b></td><td style="text-align:right;">0 - 100%</td></tr>
        </table>
    </div>
    """
    st.markdown(dict_html, unsafe_allow_html=True)
    st.markdown('<p style="color:#5F6368; font-size:11px; margin-top:10px;">Scores > 0.60 indicate high confidence regimes.</p>', unsafe_allow_html=True)

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
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    return df, pivot[['symbol', 'sector'] + sorted(recent)]

raw_df, pivot_5_df = load_data()

# 5. Fixed History Dialog (Always returns records)
@st.dialog("Full Audit Trail", width="large")
def show_audit(symbol):
    st.markdown(f'<h2 style="color:#202124;">Activity Log: {symbol}</h2>', unsafe_allow_html=True)
    # Ensure data retrieval is robust
    data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=False).head(20)
    
    if data.empty:
        st.warning("No records found in database for this ticker.")
    else:
        # Force the dataframe to be readable with a white background override
        st.dataframe(
            data[['asatdate', 'signal', 'action', 'notes']].rename(columns={'asatdate': 'Date'}),
            use_container_width=True, hide_index=True
        )

# 6. Upper Space Navigation (Zero Empty Rows)
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Ticker Search", placeholder="AAPL...").upper()
with m2: sector = st.selectbox("📁 Sector", options=["All Sectors"] + sorted(pivot_5_df['sector'].unique().tolist()))
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with m4: st.metric("Regime Status", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

# 7. Main Dashboard Split
col_grid, col_intel = st.columns([1.6, 1.4])

filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All Sectors": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    st.markdown('<h3 style="color:#202124; margin-bottom:5px;">🗓️ Recent Signal Matrix</h3>', unsafe_allow_html=True)
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
    grid_out = AgGrid(
        filtered, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, 
        allow_unsafe_jscode=True, theme="alpine", height=650, fit_columns_on_grid_load=True
    )

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        # Action Bar (Upper space leveraged)
        c_head, c_btn = st.columns([1.5, 1])
        with c_head: st.markdown(f'<h2 style="color:#202124; margin:0;">{ticker}</h2>', unsafe_allow_html=True)
        with c_btn: 
            if st.button("📊 VIEW FULL HISTORY"): show_audit(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Review Date", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # Intelligence Grid (Hard-Coded Black Labels)
        def intel_block(label, val):
            st.markdown(f'<p style="color:#202124; font-weight:700; margin-bottom:2px; margin-top:10px;">{label}: <span style="color:#1A73E8;">{val:.4f}</span></p>', unsafe_allow_html=True)
            st.progress(min(max(val, 0.0), 1.0))

        st.markdown('<h4 style="color:#5F6368; border-bottom:1px solid #DADCE0; padding-bottom:5px;">Conviction Analysis</h4>', unsafe_allow_html=True)
        intel_block("Master Conviction", d['s_hybrid'])
        intel_block("Safety Buffer", (1 - d['risk_score']))
        intel_block("Business Health", d['f_score'])
        intel_block("Institutional Flow", d['smart_money_score'])

        st.markdown('<div style="margin-top:20px; padding:15px; background-color:#E8F0FE; border-radius:5px; border:1px solid #1A73E8;">' +
                    f'<p style="color:#1A73E8; font-weight:700; margin:0;">Target Allocation: {d["final_weight"]:.2%}</p>' +
                    f'<p style="color:#202124; font-size:13px; margin:0;">Required Capital: ${d["final_dollars"]:,}</p>' +
                    '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:20px; border:1px dashed #DADCE0; text-align:center; color:#5F6368;">Select a Ticker to load Intelligence</div>', unsafe_allow_html=True)
