import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. THE FIXED DRAWER CSS (Forces content to the Right Side)
st.markdown("""
    <style>
        /* Compact Header */
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 8px 25px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Fixed Right Drawer Styling */
        .right-drawer {
            position: fixed;
            right: 0;
            top: 60px;
            width: 350px;
            height: 100vh;
            background-color: #ffffff;
            border-left: 1px solid #DADCE0;
            padding: 20px;
            z-index: 1000;
            overflow-y: auto;
            box-shadow: -2px 0 15px rgba(0,0,0,0.05);
        }

        /* High-Contrast Action Box */
        .action-box {
            background-color: #1A73E8;
            color: white !important;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        /* Metadata Grid inside Drawer */
        .data-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #F1F3F4;
        }
        .data-label { color: #5F6368; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }
        .data-value { color: #202124; font-size: 0.85rem; font-family: monospace; }
        
        /* Offset the main content so it doesn't hide behind the drawer */
        .main-content { margin-right: 360px; }
    </style>
""", unsafe_allow_html=True)

# 3. Data Engine
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate DESC", conn)
        conn.close()
        if not df.empty:
            df['date_str'] = pd.to_datetime(df['tradedate']).dt.strftime('%Y-%m-%d')
        return df
    except: return pd.DataFrame()

raw_df = load_data()

# 4. Top Hero Bar
if not raw_df.empty:
    top = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <span style="font-weight:500; font-size:1.1rem;">Signal Intelligence</span>
            <span style="font-size:0.9rem; color:#5F6368;">
                State: <b style="color:#1A73E8;">{top['final_regime']}</b> | VIX: <b>{top['vix']:.2f}</b>
            </span>
        </div>
    """, unsafe_allow_html=True)

# 5. Sidebar Controls
with st.sidebar:
    st.title("Controls")
    view_perspective = st.radio("Grid View", ["Daily Perspective", "60-Day Perspective"])
    st.markdown("---")
    ticker_search = st.text_input("🔍 Search Ticker").upper()

# 6. Main Grid (Occupies left side)
st.markdown('<div class="main-content">', unsafe_allow_html=True)
if not raw_df.empty:
    f_df = raw_df.copy()
    if ticker_search: f_df = f_df[f_df['symbol'].str.contains(ticker_search)]
    
    sig_col = 'signal' if view_perspective == "Daily Perspective" else 'signal_60d'
    recent_dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values=sig_col, aggfunc='first').reset_index()

    gb = GridOptionsBuilder.from_dataframe(pivot)
    gb.configure_column("symbol", pinned="left", width=100)
    gb.configure_selection(selection_mode="single")
    
    js_cell = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
        return {color: '#5F6368'};
    }
    """)
    for d in recent_dates: gb.configure_column(d, cellStyle=js_cell, width=150)

    grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=650, theme="balham", allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)
st.markdown('</div>', unsafe_allow_html=True)

# 7. THE FIXED RIGHT SLIDER (Metadata Drawer)
# We render this using st.markdown with raw HTML to ensure it stays pinned
selection = grid_resp.get('selected_rows')

if selection is not None and (isinstance(selection, pd.DataFrame) and not selection.empty or len(selection) > 0):
    ticker = (selection.iloc[0] if isinstance(selection, pd.DataFrame) else selection[0])['symbol']
    data = raw_df[raw_df['symbol'] == ticker].iloc[0]
    
    # Building the Metadata List HTML
    meta_html = ""
    for k, v in data.items():
        if k in ['date_str', 'tradedate', 'symbol']: continue
        val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
        meta_html += f'<div class="data-row"><span class="data-label">{k}</span><span class="data-value">{val_str}</span></div>'

    # Inject the Drawer
    st.markdown(f"""
        <div class="right-drawer">
            <h3 style="margin-top:0;">{ticker} Audit</h3>
            <div class="action-box">
                <div style="font-size:0.75rem; text-transform:uppercase;">Instruction</div>
                <div style="font-size:1.3rem; font-weight:bold;">{data['suggested_action']}</div>
                <div style="font-size:0.85rem; opacity:0.9;">{data['execution_stance']}</div>
            </div>
            <div style="margin-bottom:10px; font-weight:bold; font-size:0.9rem;">Technical Metadata</div>
            {meta_html}
        </div>
    """, unsafe_allow_html=True)
else:
    # Empty State for Drawer
    st.markdown("""
        <div class="right-drawer">
            <p style="color:#5F6368; text-align:center; margin-top:50%;">Select a ticker to view full technical metadata drawer.</p>
        </div>
    """, unsafe_allow_html=True)
