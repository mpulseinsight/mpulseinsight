import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Session State for Toggle
if 'inspector_open' not in st.session_state:
    st.session_state.inspector_open = True

# 3. Enhanced UI Styling
st.markdown("""
    <style>
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 8px 20px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .instruction-card {
            background-color: #1A73E8;
            color: white !important;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .meta-container {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            padding: 15px;
            height: 70vh;
            overflow-y: auto;
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #F1F3F4;
        }
        .meta-label { color: #5F6368; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }
        .meta-value { color: #202124; font-size: 0.85rem; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# 4. Data Engine
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

# 5. Dashboard Header
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

# 6. Adaptive Layout Logic
if st.session_state.inspector_open:
    col_main, col_side = st.columns([2.2, 0.8])
else:
    col_main, col_side = st.columns([2.95, 0.05])

# 7. Sidebar Controls
with st.sidebar:
    st.title("Controls")
    perspective = st.radio("Signal View", ["Daily", "60-Day"])
    st.markdown("---")
    # Toggle Button for Maximizing/Minimizing
    if st.session_state.inspector_open:
        if st.button("↔️ Maximize Grid (Hide Inspector)"):
            st.session_state.inspector_open = False
            st.rerun()
    else:
        if st.button("🔍 Show Inspector"):
            st.session_state.inspector_open = True
            st.rerun()
    st.markdown("---")
    ticker_filter = st.text_input("Search Ticker").upper()

# 8. Main Grid Logic
with col_main:
    if not raw_df.empty:
        f_df = raw_df.copy()
        if ticker_filter: f_df = f_df[f_df['symbol'].str.contains(ticker_filter)]
        
        sig_col = 'signal' if perspective == "Daily" else 'signal_60d'
        recent_dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
        pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values=sig_col, aggfunc='first').reset_index()

        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_column("symbol", pinned="left", width=100)
        gb.configure_selection(selection_mode="single")
        
        js_style = JsCode("""
        function(params) {
            if (!params.value) return {};
            const v = params.value.toUpperCase();
            if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
            if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
            return {color: '#5F6368'};
        }
        """)
        for d in recent_dates: gb.configure_column(d, cellStyle=js_style, width=150)

        grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=650, theme="balham", allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

# 9. The Right Side Inspector (Only renders if open)
if st.session_state.inspector_open:
    with col_side:
        st.subheader("Asset Audit")
        sel = grid_resp.get('selected_rows')
        
        if sel is not None and (isinstance(sel, pd.DataFrame) and not sel.empty or len(sel) > 0):
            ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
            data = raw_df[raw_df['symbol'] == ticker].iloc[0]
            
            # Action Banner
            st.markdown(f"""
                <div class="instruction-card">
                    <div style="font-size:0.75rem; text-transform:uppercase; font-weight:bold;">Instruction</div>
                    <div style="font-size:1.3rem; font-weight:bold;">{data['suggested_action']}</div>
                    <div style="font-size:0.85rem; opacity:0.9;">{data['execution_stance']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Vertical Data Slider (Scrollable Container)
            st.markdown('<div class="meta-container">', unsafe_allow_html=True)
            for k, v in data.items():
                if k in ['date_str', 'tradedate', 'symbol']: continue
                val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                st.markdown(f"""
                    <div class="meta-row">
                        <span class="meta-label">{k.replace('_', ' ')}</span>
                        <span class="meta-val">{val_str}</span>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Select a ticker to analyze technical metadata.")
