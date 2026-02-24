import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro Console", layout="wide", initial_sidebar_state="collapsed")

# 2. Session State for the "Slider" Position
if 'slider_state' not in st.session_state:
    st.session_state.slider_state = "open" # Options: "open", "closed"

# 3. CSS for the Right-Side Panel and Instruction Box
st.markdown("""
    <style>
        /* Compact Header */
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 10px 20px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* High-Contrast Instruction Box (Fixed white font issue) */
        .instruction-box {
            background-color: #1A73E8;
            color: #FFFFFF !important;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .instruction-box b { color: #FFFFFF !important; font-size: 1.2rem; }
        
        /* The Vertical Data Container (Scrollable) */
        .meta-slider-window {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            height: 70vh;
            overflow-y: auto;
            padding: 15px;
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #F1F3F4;
        }
        .meta-label { color: #5F6368; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; }
        .meta-value { color: #202124; font-size: 0.85rem; font-family: 'Courier New', monospace; }
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

# 5. Top Bar
if not raw_df.empty:
    top = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <span style="font-weight:500; font-size:1.1rem;">Signal Intelligence</span>
            <span style="font-size:0.9rem; color:#5F6368;">
                Market: <b style="color:#1A73E8;">{top['final_regime']}</b> | VIX: <b>{top['vix']:.2f}</b>
            </span>
        </div>
    """, unsafe_allow_html=True)

# 6. Sidebar (Left)
with st.sidebar:
    st.header("Settings")
    view_mode = st.radio("Grid View", ["Daily", "60-Day"])
    st.markdown("---")
    search_input = st.text_input("🔍 Search Ticker").upper()

# 7. Layout Toggle (The "Slider" Switch)
# This acts as the physical toggle to minimize/maximize the metadata window
c1, c2 = st.columns([2, 1])
with c1:
    if st.session_state.slider_state == "open":
        if st.button("↔️ Maximize Grid (Close Slider)"):
            st.session_state.slider_state = "closed"
            st.rerun()
    else:
        if st.button("🔍 Open Asset Slider"):
            st.session_state.slider_state = "open"
            st.rerun()

# 8. Adaptive Grid/Metadata Layout
if st.session_state.slider_state == "open":
    col_grid, col_meta = st.columns([2.2, 0.8])
else:
    col_grid, col_meta = st.columns([1, 0.001]) # Effectively 100% width

# 9. Main Matrix
with col_grid:
    if not raw_df.empty:
        f_df = raw_df.copy()
        if search_input: f_df = f_df[f_df['symbol'].str.contains(search_input)]
        
        sig_col = 'signal' if view_mode == "Daily" else 'signal_60d'
        recent_dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
        pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values=sig_col, aggfunc='first').reset_index()

        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_column("symbol", pinned="left", width=100)
        gb.configure_selection(selection_mode="single")
        
        js_color = JsCode("""
        function(params) {
            if (!params.value) return {};
            const v = params.value.toUpperCase();
            if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
            if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
            return {color: '#5F6368'};
        }
        """)
        for d in recent_dates: gb.configure_column(d, cellStyle=js_color, width=145)

        grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=600, theme="balham", allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

# 10. The Right-Side Sliding Metadata Inspector
if st.session_state.slider_state == "open":
    with col_meta:
        st.markdown("### Asset Inspector")
        selection = grid_resp.get('selected_rows')
        
        if selection is not None and (isinstance(selection, pd.DataFrame) and not selection.empty or len(selection) > 0):
            ticker = (selection.iloc[0] if isinstance(selection, pd.DataFrame) else selection[0])['symbol']
            data = raw_df[raw_df['symbol'] == ticker].iloc[0]

            # Instruction Box
            st.markdown(f"""
                <div class="instruction-box">
                    <small style="text-transform:uppercase; font-size:0.7rem; opacity:0.8;">Instruction</small><br>
                    <b>{data['suggested_action']}</b><br>
                    <div style="font-size:0.8rem; margin-top:5px; opacity:0.9;">{data['execution_stance']}</div>
                </div>
            """, unsafe_allow_html=True)

            # Scrollable Metadata List (The "Slider" content)
            st.markdown('<div class="meta-slider-window">', unsafe_allow_html=True)
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
            st.info("Select a ticker in the matrix to load technical metadata.")
