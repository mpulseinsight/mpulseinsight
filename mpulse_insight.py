import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration & Google-Style CSS
st.set_page_config(page_title="mPulse Intelligence", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        /* Google Fonts & Material Background */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        html, body, [class*="css"]  { font-family: 'Roboto', sans-serif; background-color: #F8F9FA; }
        
        /* Clean Metric Cards */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #DADCE0;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: none;
        }
        
        /* The "Google Blue" Action Banner */
        .hero-banner {
            background-color: #ffffff;
            border-bottom: 1px solid #DADCE0;
            padding: 2rem;
            margin: -3rem -5rem 2rem -5rem;
        }
        
        /* Signal Badges */
        .badge {
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 500;
            display: inline-block;
        }
        
        /* Vertical Field List (Slider Replacement) */
        .field-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #F1F3F4;
        }
        .field-label { color: #5F6368; font-size: 0.9rem; }
        .field-value { color: #202124; font-weight: 500; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# 2. Logic & Mappings
def get_logic_explanation(sig, inst, regime):
    if sig == "BULLISH" and inst == "STAY CASH":
        return f"Risk Managed: Stock momentum is positive, but the **{regime}** market regime requires defensive cash positioning."
    return f"Active Strategy: Current action is **{inst}** based on unified **{sig}** signals."

# 3. Safe Data Load
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
        st.error(f"Connect Error: {e}")
        return pd.DataFrame()

raw_df = load_data()

# 4. Top "Hero" Section (Google Search Style)
if not raw_df.empty:
    latest = raw_df.iloc[0]
    st.markdown(f"""
        <div class="hero-banner">
            <h1 style="color: #202124; font-size: 1.75rem; font-weight: 400;">Signal Intelligence</h1>
            <p style="color: #5F6368;">Market State: <b>{latest['final_regime']}</b> | VIX: <b>{latest['vix']:.2f}</b></p>
        </div>
    """, unsafe_allow_html=True)

# 5. Sidebar Controls
with st.sidebar:
    st.title("G-Console")
    view_mode = st.radio("Perspective", ["Daily Signal", "60-Day Signal", "Combined"], index=0)
    st.markdown("---")
    search = st.text_input("🔍 Search Tickers", placeholder="e.g. NVDA, TSLA").upper()
    sector = st.selectbox("Industry", ["All Sectors"] + sorted(raw_df['sector'].unique().tolist()))

# 6. Content Split: Matrix vs. Inspector
col_matrix, col_inspector = st.columns([2.2, 0.8])

if not raw_df.empty:
    # Filter Logic
    f_df = raw_df.copy()
    if search: f_df = f_df[f_df['symbol'].str.contains(search)]
    if sector != "All Sectors": f_df = f_df[f_df['sector'] == sector]

    # Signal Mapping
    def sig_map(r):
        if view_mode == "Daily Signal": return r['signal']
        if view_mode == "60-Day Signal": return r['signal_60d']
        return f"{r['signal']} / {r['signal_60d']}"
    
    f_df['display_sig'] = f_df.apply(sig_map, axis=1)
    
    # Grid Pivot
    recent_dates = sorted(f_df['date_str'].unique(), reverse=True)[:5]
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='display_sig', aggfunc='first').reset_index()

    with col_matrix:
        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_default_column(resizable=True, sortable=True)
        gb.configure_column("symbol", pinned="left", headerName="Ticker", width=100)
        
        # Google-ish Cell Styling
        js_style = JsCode("""
        function(params) {
            if (!params.value) return {};
            const v = params.value.toUpperCase();
            if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333'};
            if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F'};
            return {color: '#5F6368'};
        }
        """)
        
        for d in recent_dates:
            gb.configure_column(d, cellStyle=js_style, width=150)
            
        gb.configure_selection(selection_mode="single")
        grid_out = AgGrid(pivot, gridOptions=gb.build(), height=600, theme="balham", allow_unsafe_jscode=True)

    with col_inspector:
        st.markdown("### Asset Inspector")
        sel = grid_out.get('selected_rows')
        
        if sel is not None and len(sel) > 0:
            ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
            d = raw_df[raw_df['symbol'] == ticker].iloc[0]
            
            # Action Card
            st.markdown(f"""
                <div style="background-color:#E8F0FE; padding:15px; border-radius:8px; border-left:4px solid #1A73E8;">
                    <small style="color:#1A73E8; font-weight:bold;">STRATEGY INSTRUCTION</small><br>
                    <b style="font-size:1.2rem; color:#174EA6;">{d['suggested_action']}</b><br>
                    <p style="font-size:0.85rem; color:#3C4043; margin-top:5px;">{get_logic_explanation(d['signal'], d['suggested_action'], d['final_regime'])}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("#### Technical Scorecard")
            
            # Vertical Grid of All Fields (Slider Concept)
            fields_to_show = [
                ('s_hybrid', 'Daily Pulse'),
                ('s_structural', '60D Structure'),
                ('smart_money_score', 'Inst. Flow'),
                ('f_score', 'Quality Score'),
                ('beta', 'Market Beta'),
                ('final_weight', 'Allocation %'),
                ('kelly_fraction', 'Kelly Multiplier'),
                ('vix_regime', 'Volatility State')
            ]
            
            for field, label in fields_to_show:
                val = d.get(field, 'N/A')
                f_val = f"{val:.2%}" if "weight" in field or "fraction" in field else f"{val:.2f}" if isinstance(val, (float, int)) else str(val)
                st.markdown(f"""
                    <div class="field-row">
                        <span class="field-label">{label}</span>
                        <span class="field-value">{f_val}</span>
                    </div>
                """, unsafe_allow_html=True)
            
            if st.button("Download Data Profile"):
                st.download_button("Export CSV", d.to_csv(), f"{ticker}_audit.csv")
        else:
            st.info("Select a ticker row to inspect technical factors and execution logic.")
