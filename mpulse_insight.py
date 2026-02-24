import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Intelligence", layout="wide", initial_sidebar_state="expanded")

# 2. Refined CSS (Theme-Agnostic & High Contrast)
st.markdown("""
    <style>
        /* Compact Header Bar */
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 8px 20px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        /* Fixed Instruction Box - High Contrast */
        .instruction-card {
            background-color: #E8F0FE; /* Light Blue BG */
            border-left: 5px solid #1A73E8;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
            color: #202124 !important; /* Force Dark Text */
        }
        .instruction-label { font-size: 0.75rem; font-weight: 700; color: #1A73E8; margin-bottom: 2px; }
        .instruction-value { font-size: 1.1rem; font-weight: 700; color: #174EA6; }

        /* Vertical Meta-Slider (Right Side) */
        .meta-slider {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            height: 70vh;
            overflow-y: scroll;
            padding: 10px;
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #F1F3F4;
        }
        .meta-key { color: #5F6368; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .meta-val { color: #202124; font-size: 0.85rem; font-weight: 500; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# 3. Data Loading
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

# 4. Compact Top Bar
if not raw_df.empty:
    top = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <span style="font-size:1.1rem; font-weight:500;">Signal Intelligence</span>
            <span style="font-size:0.9rem; color:#5F6368;">
                State: <b style="color:#1A73E8;">{top['final_regime']}</b> | 
                VIX: <b style="color:#202124;">{top['vix']:.2f}</b>
            </span>
        </div>
    """, unsafe_allow_html=True)

# 5. Sidebar Navigation
with st.sidebar:
    st.header("Settings")
    view_type = st.radio("Signal Perspective", ["Daily Perspective", "60-Day Perspective"])
    st.markdown("---")
    ticker_input = st.text_input("🔍 Search Ticker").upper()

# 6. Main Content Split
col_left, col_right = st.columns([2.2, 0.8])

if not raw_df.empty:
    # Filtering
    f_df = raw_df.copy()
    if ticker_input: f_df = f_df[f_df['symbol'].str.contains(ticker_input)]
    
    # Pivot Logic
    sig_field = 'signal' if view_type == "Daily Perspective" else 'signal_60d'
    recent_dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                             values=sig_field, aggfunc='first').reset_index()

    with col_left:
        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_column("symbol", pinned="left", width=100)
        gb.configure_selection(selection_mode="single")
        
        # Color Logic
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

        grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=600, theme="balham", 
                           allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

    # 7. THE RIGHT SIDE SLIDER (Meta-Inspector)
    with col_right:
        st.markdown("### Asset Inspector")
        selection = grid_resp.get('selected_rows')
        
        if selection is not None and len(selection) > 0:
            # Sync selection across Daily/60D views
            sel_ticker = (selection.iloc[0] if isinstance(selection, pd.DataFrame) else selection[0])['symbol']
            data = raw_df[raw_df['symbol'] == sel_ticker].iloc[0]

            # Clear, Readable Instruction Card
            st.markdown(f"""
                <div class="instruction-card">
                    <div class="instruction-label">ACTIONABLE INSTRUCTION</div>
                    <div class="instruction-value">{data['suggested_action']}</div>
                    <div style="font-size:0.8rem; margin-top:5px; opacity:0.8;">
                        {data['execution_stance']} • {view_type}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # The Metadata Slider
            st.markdown('<div class="meta-slider">', unsafe_allow_html=True)
            
            # Prioritized Fields first
            priority = ['signal', 'signal_60d', 's_hybrid', 's_structural', 'risk_score', 'final_weight', 'kelly_fraction']
            
            for k in priority:
                if k in data:
                    v = f"{data[k]:.4f}" if isinstance(data[k], float) else str(data[k])
                    st.markdown(f'<div class="meta-row"><span class="meta-key">{k}</span><span class="meta-val">{v}</span></div>', unsafe_allow_html=True)
            
            st.markdown("<div style='margin: 15px 0 5px 0; font-size:0.7rem; color:#9AA0A6;'>FULL RAW METADATA</div>", unsafe_allow_html=True)
            
            # Remaining Database Fields
            for k, v in data.items():
                if k not in priority and k not in ['date_str', 'tradedate', 'symbol']:
                    v_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                    st.markdown(f'<div class="meta-row"><span class="meta-key">{k}</span><span class="meta-val">{v_str}</span></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Select a ticker to view instructions and scrollable metadata.")
