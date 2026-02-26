import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration - Restoring the Left Sidebar
st.set_page_config(
    page_title="mPulse Pro Console", 
    layout="wide", 
    initial_sidebar_state="expanded" # This ensures the left slider is visible
)

# 2. Professional Terminal CSS
st.markdown("""
    <style>
        /* Base Background */
        .stApp { background-color: #fcfdfe; }
        
        /* Command Header */
        .terminal-header {
            background: #1a202c;
            color: #e2e8f0;
            padding: 1rem 2rem;
            margin: -3rem -5rem 1.5rem -5rem;
            border-bottom: 4px solid #3182ce;
        }

        /* Intelligence Card Styling */
        .intel-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-top: 1rem;
        }

        /* Metric Blocks */
        .metric-box {
            border-left: 4px solid #3182ce;
            background: #f7fafc;
            padding: 10px 15px;
            border-radius: 0 8px 8px 0;
        }
        .metric-label { font-size: 0.7rem; font-weight: 700; color: #4a5568; text-transform: uppercase; letter-spacing: 0.05em; }
        .metric-value { font-size: 1.25rem; font-weight: 800; color: #2d3748; font-family: 'Inter', sans-serif; }

        /* Diagnostic Warning */
        .diag-alert {
            background-color: #fffaf0;
            border: 1px solid #feebc8;
            padding: 1rem;
            border-radius: 8px;
            color: #7b341e;
            font-size: 0.9rem;
            border-left: 5px solid #ed8936;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Robust Data Engine
@st.cache_data(ttl=60)
def load_and_process_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"], 
            user=creds["user"], password=creds["password"], sslmode="require"
        )
        # Fetching all relevant columns
        df = pd.read_sql("SELECT * FROM mpulse_execution_results", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        df['tradedate'] = pd.to_datetime(df['tradedate'])
        df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        
        # Rank signals for sorting: Buy/Bullish float to top
        rank_map = {'BUY': 5, 'BULLISH': 4, 'HOLD': 3, 'BEARISH': 2, 'SELL': 1}
        df['rank_score'] = df['signal'].fillna('').str.upper().apply(
            lambda x: next((v for k, v in rank_map.items() if k in x), 0)
        )
        return df
    except Exception as e:
        st.error(f"Database Connection Offline: {e}")
        return pd.DataFrame()

raw_df = load_and_process_data()

# 4. Sidebar (The Left Slider)
with st.sidebar:
    st.image("https://www.gstatic.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png", width=100) # Placeholder for your logo
    st.title("mPulse Controls")
    search_query = st.text_input("🔍 Quick Asset Search", "").upper()
    filter_regime = st.multiselect("Market Regime", options=raw_df['final_regime'].unique() if not raw_df.empty else [])
    st.divider()
    st.info("System Status: Operational\nData Feed: Real-time")

# 5. Top Level: Global Market Pulse
st.markdown("""
    <div class="terminal-header">
        <h2 style="margin:0; font-size:1.5rem;">Terminal: Market Intelligence Hub</h2>
    </div>
""", unsafe_allow_html=True)

if not raw_df.empty:
    # Get latest systemic metrics (Regime, VIX)
    global_ref = raw_df.sort_values('tradedate', ascending=False).iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current Regime", global_ref.get('final_regime', 'N/A'))
    with col2: st.metric("Volatility Index", f"{global_ref.get('vix', 0):.2f}")
    with col3: 
        z = global_ref.get('zscore', 0)
        st.metric("Systemic Z-Score", f"{z:.2f}", delta=f"{z:+.2f}")
    with col4: st.metric("Total Tickers", len(raw_df['symbol'].unique()))

# 6. Center: Alpha Signal Matrix (Last 5 Days)
st.subheader("📡 5-Day Alpha Matrix")
if not raw_df.empty:
    recent_dates = sorted(raw_df['date_str'].unique(), reverse=True)[:5]
    latest_date = recent_dates[0]
    
    # Filter & Sort
    f_df = raw_df[raw_df['date_str'].isin(recent_dates)].copy()
    if search_query:
        f_df = f_df[f_df['symbol'].str.contains(search_query)]
    
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index()
    latest_ranks = f_df[f_df['date_str'] == latest_date][['symbol', 'rank_score']]
    pivot = pivot.merge(latest_ranks, on='symbol', how='left').sort_values(by='rank_score', ascending=False).fillna("—")

    gb = GridOptionsBuilder.from_dataframe(pivot.drop(columns=['rank_score']))
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=120)
    gb.configure_selection(selection_mode="single")
    
    js_color = JsCode("""
    function(params) {
        if (!params.value || params.value === '—') return {color: '#cbd5e0'};
        const v = params.value.toUpperCase();
        if (v.includes('BUY')) return {backgroundColor: '#c6f6d5', color: '#22543d', fontWeight: 'bold'};
        if (v.includes('SELL')) return {backgroundColor: '#fed7d7', color: '#822727', fontWeight: 'bold'};
        return {color: '#4a5568'};
    }
    """)
    for d in recent_dates: gb.configure_column(d, cellStyle=js_color)

    grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=350, theme="balham", allow_unsafe_jscode=True)

# 7. Bottom: Asset Intelligence hub
st.divider()
selection = grid_resp.get('selected_rows')

# Helper: Standardize Selection
selected_row = None
if selection is not None:
    if isinstance(selection, pd.DataFrame) and not selection.empty: selected_row = selection.iloc[0]
    elif isinstance(selection, list) and len(selection) > 0: selected_row = selection[0]

if selected_row is not None:
    ticker = selected_row['symbol']
    
    # FIX: Find the latest record FOR THIS TICKER that actually has technical data
    # This prevents the "Evaluation Suspended" error if today's data is empty
    ticker_history = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False)
    
    # We look for the most recent row where Z-Score is not Null
    valid_data_rows = ticker_history.dropna(subset=['zscore', 'rsi', 'atr'])
    
    if valid_data_rows.empty:
        st.markdown(f"""
            <div class="diag-alert">
                <strong>🚫 Data Integrity Warning: {ticker}</strong><br>
                This asset has no valid Z-Score or RSI records in the database. 
                Please verify the data feed for this ticker.
            </div>
        """, unsafe_allow_html=True)
    else:
        curr = valid_data_rows.iloc[0]
        
        st.markdown(f"### 🛡️ Intelligence Hub: {ticker}")
        st.markdown('<div class="intel-card">', unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Action Logic
            sig = str(curr.get('signal', '')).upper()
            action = str(curr.get('suggested_action', 'HOLD')).upper()
            display_action = "ACCUMULATE" if ("BULLISH" in sig and "CASH" in action) else action
            
            st.markdown(f'<div class="metric-box"><div class="metric-label">Execution Stance</div><div class="metric-value">{display_action}</div></div>', unsafe_allow_html=True)
        
        with c2:
            st.markdown(f'<div class="metric-box"><div class="metric-label">Theory Z-Score</div><div class="metric-value">{curr["zscore"]:.2f}</div></div>', unsafe_allow_html=True)
        
        with c3:
            st.markdown(f'<div class="metric-box"><div class="metric-label">RSI (Momentum)</div><div class="metric-value">{curr.get("rsi", 0):.1f}</div></div>', unsafe_allow_html=True)
            
        with c4:
            st.markdown(f'<div class="metric-box"><div class="metric-label">Volatility (ATR)</div><div class="metric-value">{curr.get("atr", 0):.2f}</div></div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Dictionary / Range Explainer
        with st.expander("📚 Theory Dictionary & Thresholds"):
            st.markdown("""
            | Metric | Professional Definition | Trade Zone Range |
            | :--- | :--- | :--- |
            | **Z-Score** | Standard deviation from price mean. | **> +1.5** (Overextended), **< -1.5** (Undervalued) |
            | **RSI** | Velocity of price movement. | **< 30** (Strong Buy Zone), **> 70** (Take Profit) |
            | **ATR** | Volatility based on true ranges. | Used to determine Stop Loss distance. |
            """)
            st.json(curr.to_dict())
else:
    st.info("💡 Select an asset from the 5-Day Alpha Matrix to view the Command Center diagnostics.")
