import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro", layout="wide", initial_sidebar_state="expanded")

# 2. Google-Standard UI Styling
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif; background-color: #F8F9FA; }
        
        /* Compact Top Bar */
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 10px 25px;
            margin: -3rem -5rem 1rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .hero-title { font-size: 1.2rem; font-weight: 500; color: #202124; margin: 0; }
        .hero-stats { font-size: 0.9rem; color: #5F6368; margin: 0; }

        /* Vertical Side Slider (Inspector) */
        .inspector-container {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            border-radius: 8px;
            padding: 16px;
            height: 75vh;
            overflow-y: auto;
        }
        .field-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #F1F3F4;
        }
        .field-label { color: #5F6368; font-size: 0.8rem; text-transform: uppercase; font-weight: 600; }
        .field-value { color: #202124; font-weight: 500; font-size: 0.9rem; text-align: right; }
        
        /* Strategy Badge */
        .strategy-card {
            background-color: #E8F0FE;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #1A73E8;
            margin-bottom: 15px;
        }
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
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

raw_df = load_data()

# 4. Top Hero Bar (Compact)
if not raw_df.empty:
    latest_row = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <p class="hero-title">Signal Intelligence</p>
            <p class="hero-stats">
                Market State: <span style="color:#1A73E8; font-weight:bold;">{latest_row['final_regime']}</span> | 
                VIX: <span style="color:#202124; font-weight:bold;">{latest_row['vix']:.2f}</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

# 5. Sidebar Navigation
with st.sidebar:
    st.markdown("### Grid Perspective")
    perspective = st.radio("Primary Focus", ["Daily Signals", "60-Day Signals"], index=0)
    st.markdown("---")
    ticker_search = st.text_input("🔍 Filter Ticker").upper()
    sector_search = st.selectbox("📂 Sector", ["All"] + sorted(raw_df['sector'].unique().tolist()))

# 6. Main Dashboard Split
col_main, col_side = st.columns([2.3, 0.7])

if not raw_df.empty:
    # Filter Logic
    df_f = raw_df.copy()
    if ticker_search: df_f = df_f[df_f['symbol'].str.contains(ticker_search)]
    if sector_search != "All": df_f = df_f[df_f['sector'] == sector_search]

    # Map the Grid Pivot based on Perspective
    target_signal = 'signal' if perspective == "Daily Signals" else 'signal_60d'
    recent_dates = sorted(df_f['date_str'].unique(), reverse=True)[:5]
    
    pivot = df_f.pivot_table(index=['symbol', 'sector'], columns='date_str', 
                             values=target_signal, aggfunc='first').reset_index()

    with col_main:
        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_column("symbol", pinned="left", headerName="Ticker", width=100)
        gb.configure_selection(selection_mode="single")
        
        # Professional Cell Coloring
        js_style = JsCode("""
        function(params) {
            if (!params.value) return {};
            const v = params.value.toUpperCase();
            if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
            if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
            return {color: '#5F6368'};
        }
        """)
        for d in recent_dates:
            gb.configure_column(d, cellStyle=js_style, width=140)

        grid_out = AgGrid(pivot, gridOptions=gb.build(), height=650, theme="balham", 
                          allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

    # 7. Vertical Sidebar Slider (Asset Inspector)
    with col_side:
        st.markdown("### Asset Inspector")
        # Direct lookup to ensure syncing across perspectives
        sel = grid_out.get('selected_rows')
        
        if sel is not None and len(sel) > 0:
            # Handle both list and dataframe formats from AgGrid
            selected_ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
            
            # Fetch the specific row for this ticker
            ticker_data = raw_df[raw_df['symbol'] == selected_ticker].iloc[0]
            
            # Strategy Instruction Card
            st.markdown(f"""
                <div class="strategy-card">
                    <small>INSTRUCTION</small><br>
                    <b style="font-size:1.1rem; color:#174EA6;">{ticker_data['suggested_action']}</b><br>
                    <p style="font-size:0.8rem; color:#3C4043; margin-top:4px;">
                        {ticker_data['execution_stance']} aligned with {perspective}.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # Vertical Slider (Field List)
            st.markdown('<div class="inspector-container">', unsafe_allow_html=True)
            
            # Grouping fields for better readability
            important_fields = ['signal', 'signal_60d', 's_hybrid', 's_structural', 'final_weight', 'kelly_fraction', 'beta', 'risk_score', 'smart_money_score', 'f_score', 'vix']
            
            # Display important ones first
            for field in important_fields:
                if field in ticker_data:
                    val = ticker_data[field]
                    # Format numbers
                    disp = f"{val:.2%}" if "weight" in field else f"{val:.4f}" if isinstance(val, float) else str(val)
                    st.markdown(f"""<div class="field-row"><span class="field-label">{field}</span><span class="field-value">{disp}</span></div>""", unsafe_allow_html=True)
            
            st.markdown("<br><small>ALL DATA POINTS</small>", unsafe_allow_html=True)
            # Display remaining fields
            for field, val in ticker_data.items():
                if field not in important_fields and field not in ['date_str', 'tradedate']:
                    disp = f"{val:.4f}" if isinstance(val, float) else str(val)
                    st.markdown(f"""<div class="field-row"><span class="field-label">{field}</span><span class="field-value">{disp}</span></div>""", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Select a ticker in the matrix to inspect all technical fields.")
