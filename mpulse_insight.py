import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro Console", layout="wide", initial_sidebar_state="collapsed")

# 2. Session State
if 'slider_state' not in st.session_state:
    st.session_state.slider_state = "open"

# 3. Enhanced CSS
st.markdown("""
    <style>
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 10px 20px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .instruction-box {
            background-color: #1A73E8;
            color: #FFFFFF !important;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .instruction-box b { color: #FFFFFF !important; font-size: 1.1rem; }
        
        /* Fixed Slider Styling */
        .meta-slider-window {
            background-color: #f8f9fa;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            height: 400px;
            overflow-y: auto;
            padding: 12px;
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #eee;
        }
        .meta-label { color: #5F6368; font-size: 0.7rem; font-weight: bold; text-transform: uppercase; }
        /* Matched this class name to the HTML below */
        .meta-value { color: #202124; font-size: 0.8rem; font-family: 'Courier New', monospace; font-weight: 600; }
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
    except:
        # Mock data for demonstration if DB fails
        return pd.DataFrame()

raw_df = load_data()

# 5. Sidebar & Trade Zone Filter
with st.sidebar:
    st.header("Console Controls")
    view_mode = st.radio("Grid View", ["Daily", "60-Day"])
    search_input = st.text_input("🔍 Search Ticker").upper()
    
    st.markdown("---")
    # THE REQUESTED FEATURE: Trade Zone Checkbox
    trade_zone_only = st.checkbox("🚀 Trade Zone Only", help="Filter for high-conviction Bullish/Buy signals")

# 6. Top Bar
if not raw_df.empty:
    top = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <span style="font-weight:500; font-size:1.1rem;">Signal Intelligence</span>
            <span style="font-size:0.9rem; color:#5F6368;">
                Market: <b style="color:#1A73E8;">{top.get('final_regime', 'N/A')}</b> | VIX: <b>{top.get('vix', 0):.2f}</b>
            </span>
        </div>
    """, unsafe_allow_html=True)

# 7. Layout Logic
if st.session_state.slider_state == "open":
    col_grid, col_meta = st.columns([2.2, 0.8])
    toggle_label = "↔️ Maximize Grid"
else:
    col_grid = st.container()
    col_meta = None
    toggle_label = "🔍 Open Inspector"

if st.button(toggle_label):
    st.session_state.slider_state = "closed" if st.session_state.slider_state == "open" else "open"
    st.rerun()

# 8. Main Matrix Processing
with col_grid:
    if not raw_df.empty:
        f_df = raw_df.copy()
        sig_col = 'signal' if view_mode == "Daily" else 'signal_60d'
        
        # Apply Search
        if search_input:
            f_df = f_df[f_df['symbol'].str.contains(search_input)]
        
        # Apply Trade Zone Filter Logic
        if trade_zone_only:
            # Filter for rows where signal contains BUY or BULLISH
            f_df = f_df[f_df[sig_col].str.contains('BUY|BULLISH', case=False, na=False)]

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
        for d in recent_dates: gb.configure_column(d, cellStyle=js_color, width=140)

        grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=500, theme="balham", allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

# 9. Fixed Asset Inspector
if st.session_state.slider_state == "open" and col_meta:
    with col_meta:
        st.subheader("Asset Inspector")
        selection = grid_resp.get('selected_rows')
        
        # Robust selection check for newer versions of AgGrid
        selected_data = None
        if selection is not None:
            if isinstance(selection, pd.DataFrame) and not selection.empty:
                selected_data = selection.iloc[0]
            elif isinstance(selection, list) and len(selection) > 0:
                selected_data = selection[0]

        if selected_data is not None:
            ticker = selected_data['symbol']
            # Get the full record for the selected ticker
            full_record = raw_df[raw_df['symbol'] == ticker].iloc[0]

            st.markdown(f"""
                <div class="instruction-box">
                    <small style="text-transform:uppercase; font-size:0.7rem; opacity:0.8;">Primary Action</small><br>
                    <b>{full_record.get('suggested_action', 'HOLD')}</b><br>
                    <div style="font-size:0.8rem; margin-top:5px; opacity:0.9;">{full_record.get('execution_stance', 'No specific stance')}</div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="meta-slider-window">', unsafe_allow_html=True)
            for k, v in full_record.items():
                if k in ['date_str', 'tradedate', 'symbol']: continue
                val_display = f"{v:.4f}" if isinstance(v, float) else str(v)
                st.markdown(f"""
                    <div class="meta-row">
                        <span class="meta-label">{k.replace('_', ' ')}</span>
                        <span class="meta-value">{val_display}</span>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Select a row in the grid to inspect technical factors.")
