import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Intelligence", layout="wide", initial_sidebar_state="expanded")

# 2. State Management for the "Slider/Drawer"
if 'drawer_open' not in st.session_state:
    st.session_state.drawer_open = True

# 3. Custom CSS for the "Right Slide-Out" Look
st.markdown("""
    <style>
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 8px 25px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        /* The Inspector 'Drawer' Styling */
        .meta-drawer {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            padding: 15px;
            height: 75vh;
            display: flex;
            flex-direction: column;
        }

        .instruction-card {
            background-color: #1A73E8;
            color: white !important;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 10px;
        }

        /* The Vertical Data Slider (Scrollable Area) */
        .vertical-slider {
            flex-grow: 1;
            overflow-y: scroll;
            margin-top: 10px;
            padding-right: 5px;
            border-top: 1px solid #eee;
        }

        .data-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #F8F9FA;
        }
        .label { color: #5F6368; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }
        .val { color: #202124; font-size: 0.85rem; font-family: monospace; }
        
        /* Sidebar Button Styling */
        .stButton>button { width: 100%; border-radius: 20px; }
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

# 5. Header
if not raw_df.empty:
    top = raw_df.iloc[0]
    st.markdown(f"""<div class="hero-banner">
        <span style="font-weight:500; font-size:1.1rem;">Signal Intelligence</span>
        <span style="font-size:0.9rem; color:#5F6368;">
            Market: <b style="color:#1A73E8;">{top['final_regime']}</b> | VIX: <b>{top['vix']:.2f}</b>
        </span>
    </div>""", unsafe_allow_html=True)

# 6. Sidebar Controls
with st.sidebar:
    st.title("Navigation")
    perspective = st.radio("Grid Focus", ["Daily", "60-Day"])
    st.markdown("---")
    # Toggle logic for the right-side "Slider"
    if st.session_state.drawer_open:
        if st.button("⬅️ Close Inspector"):
            st.session_state.drawer_open = False
            st.rerun()
    else:
        if st.button("➡️ Open Inspector"):
            st.session_state.drawer_open = True
            st.rerun()
    st.markdown("---")
    search_q = st.text_input("Ticker Search").upper()

# 7. Layout Management
if st.session_state.drawer_open:
    col_main, col_drawer = st.columns([2.2, 0.8])
else:
    col_main, col_drawer = st.columns([2.98, 0.02])

# 8. Main Grid
with col_main:
    if not raw_df.empty:
        f_df = raw_df.copy()
        if search_q: f_df = f_df[f_df['symbol'].str.contains(search_q)]
        
        sig_col = 'signal' if perspective == "Daily" else 'signal_60d'
        dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
        pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values=sig_col, aggfunc='first').reset_index()

        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_column("symbol", pinned="left", width=90)
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
        for d in dates: gb.configure_column(d, cellStyle=js_color, width=150)

        grid_out = AgGrid(pivot, gridOptions=gb.build(), height=650, theme="balham", allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

# 9. The Right Side "Slider/Drawer"
if st.session_state.drawer_open:
    with col_drawer:
        st.markdown("### Asset Audit")
        sel = grid_out.get('selected_rows')
        
        if sel is not None and (isinstance(sel, pd.DataFrame) and not sel.empty or len(sel) > 0):
            ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
            data = raw_df[raw_df['symbol'] == ticker].iloc[0]

            # Strategy Banner
            st.markdown(f"""
                <div class="instruction-card">
                    <small>INSTRUCTION</small><br>
                    <b style="font-size:1.2rem;">{data['suggested_action']}</b><br>
                    <small>{data['execution_stance']}</small>
                </div>
            """, unsafe_allow_html=True)

            # Metadata Scrollable Slider Area
            st.markdown('<div class="meta-drawer">', unsafe_allow_html=True)
            st.markdown("<b>Technical Attributes</b>", unsafe_allow_html=True)
            
            st.markdown('<div class="vertical-slider">', unsafe_allow_html=True)
            for k, v in data.items():
                if k in ['date_str', 'tradedate', 'symbol']: continue
                val_formatted = f"{v:.4f}" if isinstance(v, float) else str(v)
                st.markdown(f"""
                    <div class="data-row">
                        <span class="label">{k.replace('_', ' ')}</span>
                        <span class="val">{val_formatted}</span>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
        else:
            st.info("Select a ticker to activate the inspector drawer.")
