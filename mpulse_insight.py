import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Config
st.set_page_config(page_title="mPulse Pro Console", layout="wide")

# 2. Google-Style CSS
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .hero-banner { background-color: white; border-bottom: 1px solid #dadce0; padding: 15px 25px; margin: -3rem -5rem 2rem -5rem; display: flex; justify-content: space-between; align-items: center; }
        
        /* Analysis Card */
        .analysis-card { background: white; border: 1px solid #dadce0; border-radius: 8px; padding: 20px; margin-top: 20px; box-shadow: 0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15); }
        .metric-pill { background: #f1f3f4; border-radius: 4px; padding: 4px 8px; font-family: monospace; font-size: 0.85rem; color: #3c4043; border: 1px solid #e8eaed; }
        .dictionary-header { color: #1a73e8; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; margin-top: 15px; border-bottom: 1px solid #e8eaed; padding-bottom: 5px; }
        .action-highlight { font-size: 1.4rem; font-weight: 700; color: #202124; }
        
        /* Range Bar Simulation */
        .range-container { width: 100%; background: #e8eaed; height: 8px; border-radius: 4px; margin: 10px 0; position: relative; }
        .range-fill { background: #1a73e8; height: 100%; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# 3. Data Engine (Last 5 Days + Ranking)
@st.cache_data(ttl=60)
def load_and_rank_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        df['tradedate'] = pd.to_datetime(df['tradedate'])
        df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        
        # Ranking Logic: Strongest signals first
        rank_map = {'BUY': 5, 'BULLISH': 4, 'HOLD': 3, 'BEARISH': 2, 'SELL': 1}
        df['rank_score'] = df['signal'].str.upper().map(lambda x: next((v for k, v in rank_map.items() if k in str(x)), 0))
        
        return df
    except:
        return pd.DataFrame()

raw_df = load_and_rank_data()

# 4. Filter Logic
with st.sidebar:
    st.subheader("Console Settings")
    trade_zone_only = st.checkbox("🚀 Trade Zone Focus", help="Shows only Bullish/Buy signals")
    search_input = st.text_input("🔍 Search Ticker").upper()

# 5. Main Grid Display
if not raw_df.empty:
    recent_5_dates = sorted(raw_df['date_str'].unique(), reverse=True)[:5]
    latest_date = recent_5_dates[0]
    
    # Filter to 5 days
    f_df = raw_df[raw_df['date_str'].isin(recent_5_dates)].copy()
    if trade_zone_only: f_df = f_df[f_df['rank_score'] >= 4]
    if search_input: f_df = f_df[f_df['symbol'].str.contains(search_input)]

    # Pivot & Sort by Rank
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index()
    latest_ranks = f_df[f_df['date_str'] == latest_date][['symbol', 'rank_score']]
    pivot = pivot.merge(latest_ranks, on='symbol', how='left').sort_values(by='rank_score', ascending=False)

    st.subheader("Market Signal Matrix (Last 5 Days)")
    
    gb = GridOptionsBuilder.from_dataframe(pivot.drop(columns=['rank_score']))
    gb.configure_column("symbol", pinned="left", width=110, headerName="Asset")
    gb.configure_selection(selection_mode="single")
    
    js_color = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#e6f4ea', color: '#137333', fontWeight: 'bold'};
        if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#fce8e6', color: '#c5221f', fontWeight: 'bold'};
        return {color: '#5f6368'};
    }
    """)
    for d in recent_5_dates: gb.configure_column(d, cellStyle=js_color, width=135)

    grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=400, theme="balham", allow_unsafe_jscode=True, update_mode=GridUpdateMode.SELECTION_CHANGED)

# 6. Google-Style Intelligence Hub (The "Expander" Logic)
selection = grid_resp.get('selected_rows')

# FIXED: Safe check for pandas selection to avoid ValueError
selected_data = None
if selection is not None:
    if isinstance(selection, pd.DataFrame) and not selection.empty:
        selected_data = selection.iloc[0]
    elif isinstance(selection, list) and len(selection) > 0:
        selected_data = selection[0]

if selected_data is not None:
    ticker = selected_data['symbol']
    full_data = raw_df[(raw_df['symbol'] == ticker) & (raw_df['date_str'] == latest_date)].iloc[0]
    
    # Meaningful Action Override
    sig = str(full_data.get('signal', '')).upper()
    action = str(full_data.get('suggested_action', 'HOLD')).upper()
    if ("BULLISH" in sig or "BUY" in sig) and "CASH" in action:
        display_action = "ACCUMULATE ON DIP"
        display_stance = "Technical indicators are prime; wait for intra-day volume confirmation."
    else:
        display_action = action
        display_stance = full_data.get('execution_stance', 'Monitoring baseline.')

    st.markdown(f"""
        <div class="analysis-card">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div>
                    <span style="color:#5f6368; font-size:0.8rem; text-transform:uppercase;">Selected Asset</span>
                    <div class="action-highlight">{ticker} — {display_action}</div>
                    <div style="color:#5f6368; margin-top:5px;">{display_stance}</div>
                </div>
                <div style="text-align:right;">
                    <span style="color:#1a73e8; font-weight:600;">{full_data.get('sector', 'General')}</span><br>
                    <small>Last Updated: {latest_date}</small>
                </div>
            </div>
    """, unsafe_allow_html=True)

    # Range / Technical Metrics Display
    cols = st.columns(3)
    metrics_to_show = ['vix', 'atr', 'rsi', 'adx', 'mfi'] # Customize based on your DB columns
    
    for i, m in enumerate(metrics_to_show):
        val = full_data.get(m, 0)
        with cols[i % 3]:
            st.markdown(f"**{m.upper()}**")
            st.markdown(f'<div class="metric-pill">{val:.2f}</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

    # The Collapsible Deep Dive & Dictionary
    with st.expander("View Technical Dictionary & Factor Deep-Dive"):
        st.markdown('<div class="dictionary-header">Metric Dictionary</div>', unsafe_allow_html=True)
        dict_cols = st.columns(2)
        with dict_cols[0]:
            st.write("**VIX:** Market volatility index. High (>25) implies fear.")
            st.write("**ATR:** Average True Range. Measures asset price movement.")
        with dict_cols[1]:
            st.write("**RSI:** Relative Strength Index. >70 is overbought, <30 oversold.")
            st.write("**ADX:** Average Directional Index. Higher values mean a stronger trend.")

        st.markdown('<div class="dictionary-header">Full Data Trace</div>', unsafe_allow_html=True)
        st.json(full_data.to_dict())

else:
    st.info("💡 Select an asset from the grid above to view the Intelligence Card.")
