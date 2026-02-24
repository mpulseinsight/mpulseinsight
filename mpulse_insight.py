import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Refined CSS for the "Slider Window"
st.markdown("""
    <style>
        /* Compact Header */
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 6px 20px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
        }
        
        /* The Inspector Box (The 'Slider' Window) */
        .inspector-window {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        /* High-Contrast Instruction Box */
        .instruction-card {
            background-color: #1A73E8;
            color: #ffffff !important;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
        }

        /* Metadata List */
        .meta-scroll {
            height: 60vh;
            overflow-y: auto;
            border-top: 1px solid #eee;
            margin-top: 10px;
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #F8F9FA;
        }
        .meta-label { color: #5F6368; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; }
        .meta-value { color: #202124; font-size: 0.85rem; font-family: 'Courier New', monospace; }
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

# 4. Top Hero Bar
if not raw_df.empty:
    top = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <span style="font-weight:500;">Signal Intelligence</span>
            <span style="font-size:0.85rem; color:#5F6368;">
                State: <b style="color:#1A73E8;">{top['final_regime']}</b> | VIX: <b>{top['vix']:.2f}</b>
            </span>
        </div>
    """, unsafe_allow_html=True)

# 5. Sidebar - Perspective & Hide Toggle
with st.sidebar:
    st.header("Dashboard Control")
    view_type = st.radio("Signal Mode", ["Daily", "60-Day"])
    show_inspector = st.checkbox("Show Asset Inspector", value=True)
    st.markdown("---")
    search_ticker = st.text_input("🔍 Ticker Search").upper()

# 6. Content Split: Adjust ratio based on "Minimize" toggle
if show_inspector:
    col_main, col_side = st.columns([2.3, 0.7])
else:
    col_main, col_side = st.columns([3, 0.01]) # Minimize side column

if not raw_df.empty:
    # Filter and Pivot
    f_df = raw_df.copy()
    if search_ticker: f_df = f_df[f_df['symbol'].str.contains(search_ticker)]
    
    sig_field = 'signal' if view_type == "Daily" else 'signal_60d'
    recent_dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                             values=sig_field, aggfunc='first').reset_index()

    with col_main:
        st.markdown(f"### Market Matrix ({view_type})")
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
        for d in recent_dates: gb.configure_column(d, cellStyle=js_color, width=150)

        grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=650, theme="balham", 
                           allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

    # 7. THE RIGHT SIDE SLIDER WINDOW
    if show_inspector:
        with col_side:
            st.markdown("### Asset Inspector")
            selection = grid_resp.get('selected_rows')
            
            if selection is not None and len(selection) > 0:
                ticker = (selection.iloc[0] if isinstance(selection, pd.DataFrame) else selection[0])['symbol']
                data = raw_df[raw_df['symbol'] == ticker].iloc[0]

                # 1. Instruction Card
                st.markdown(f"""
                    <div class="instruction-card">
                        <div style="font-size:0.7rem; opacity:0.9;">SUGGESTED ACTION</div>
                        <div style="font-size:1.2rem; font-weight:bold;">{data['suggested_action']}</div>
                        <div style="font-size:0.8rem; margin-top:4px; opacity:0.8;">{data['execution_stance']}</div>
                    </div>
                """, unsafe_allow_html=True)

                # 2. Meta Slider Window
                st.markdown('<div class="inspector-window">', unsafe_allow_html=True)
                st.markdown("<strong>Technical Metadata</strong>", unsafe_allow_html=True)
                
                st.markdown('<div class="meta-scroll">', unsafe_allow_html=True)
                # Show all 40+ fields dynamically
                for k, v in data.items():
                    if k in ['date_str', 'tradedate', 'symbol']: continue
                    
                    # Formatting values
                    v_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                    
                    st.markdown(f"""
                        <div class="meta-row">
                            <span class="meta-label">{k.replace('_', ' ')}</span>
                            <span class="meta-val">{v_str}</span>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                st.info("👆 Select a row in the matrix to load metadata.")
