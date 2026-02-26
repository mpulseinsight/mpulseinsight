import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro Console", layout="wide", initial_sidebar_state="expanded")

# 2. Professional Terminal CSS
st.markdown("""
    <style>
        .stApp { background-color: #f8f9fa; }
        header { visibility: hidden; }
        
        /* Command Header */
        .terminal-header {
            background: #1a73e8;
            color: white;
            padding: 1.5rem;
            margin: -3rem -5rem 1.5rem -5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* Intelligence Card */
        .intel-card {
            background: white;
            border: 1px solid #dadce0;
            border-radius: 8px;
            padding: 20px;
            margin-top: 15px;
        }

        /* Metric Blocks */
        .metric-box {
            border-bottom: 3px solid #1a73e8;
            background: #f1f3f4;
            padding: 12px;
            border-radius: 4px;
            text-align: center;
        }
        .metric-label { font-size: 0.7rem; font-weight: 700; color: #5f6368; text-transform: uppercase; }
        .metric-value { font-size: 1.2rem; font-weight: 600; color: #202124; }
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
        df = pd.read_sql("SELECT * FROM mpulse_execution_results", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        # Clean column names to lowercase to avoid KeyErrors
        df.columns = [c.lower() for c in df.columns]
        
        if 'tradedate' in df.columns:
            df['tradedate'] = pd.to_datetime(df['tradedate'])
            df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        
        # Ranking Logic
        rank_map = {'BUY': 5, 'BULLISH': 4, 'HOLD': 3, 'BEARISH': 2, 'SELL': 1}
        if 'signal' in df.columns:
            df['rank_score'] = df['signal'].fillna('').str.upper().apply(
                lambda x: next((v for k, v in rank_map.items() if k in x), 0)
            )
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

raw_df = load_and_process_data()

# 4. Sidebar (Left Slider)
with st.sidebar:
    st.title("mPulse Pro")
    st.markdown("---")
    search_query = st.text_input("🔍 Search Asset", "").upper()
    st.divider()
    st.caption("v3.2.0 Operating System")

# 5. Global Status Bar
st.markdown('<div class="terminal-header"><h2>Market Intelligence Command Center</h2></div>', unsafe_allow_html=True)

if not raw_df.empty:
    latest_global = raw_df.sort_values('tradedate', ascending=False).iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Regime", latest_global.get('final_regime', 'N/A'))
    c2.metric("VIX", f"{latest_global.get('vix', 0):.2f}")
    c3.metric("Assets Tracked", len(raw_df['symbol'].unique()))

# 6. Main Matrix (Last 5 Days)
if not raw_df.empty:
    recent_dates = sorted(raw_df['date_str'].unique(), reverse=True)[:5]
    latest_date = recent_dates[0]
    
    f_df = raw_df[raw_df['date_str'].isin(recent_dates)].copy()
    if search_query:
        f_df = f_df[f_df['symbol'].str.contains(search_query)]
    
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index()
    
    # Re-merge rank for sorting
    latest_ranks = f_df[f_df['date_str'] == latest_date][['symbol', 'rank_score']].drop_duplicates('symbol')
    pivot = pivot.merge(latest_ranks, on='symbol', how='left').sort_values(by='rank_score', ascending=False)

    gb = GridOptionsBuilder.from_dataframe(pivot.drop(columns=['rank_score'], errors='ignore'))
    gb.configure_column("symbol", pinned="left", headerName="Ticker")
    gb.configure_selection(selection_mode="single")
    
    js_color = JsCode("""
    function(params) {
        if (!params.value) return {color: '#bdc3c7'};
        const v = params.value.toUpperCase();
        if (v.includes('BUY')) return {backgroundColor: '#e6f4ea', color: '#137333', fontWeight: 'bold'};
        if (v.includes('SELL')) return {backgroundColor: '#fce8e6', color: '#c5221f', fontWeight: 'bold'};
        return {color: '#5f6368'};
    }
    """)
    for d in recent_dates: gb.configure_column(d, cellStyle=js_color)

    grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=350, theme="balham", allow_unsafe_jscode=True)

# 7. Intelligence Hub (Meaningful Info)
selection = grid_resp.get('selected_rows')
selected_row = None
if selection is not None:
    if isinstance(selection, pd.DataFrame) and not selection.empty: selected_row = selection.iloc[0]
    elif isinstance(selection, list) and len(selection) > 0: selected_row = selection[0]

if selected_row is not None:
    ticker = selected_row['symbol']
    # Filter history and drop completely empty columns to find "Meaningful" data
    ticker_history = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False)
    
    # Dynamic column identification to prevent KeyErrors
    available_cols = ticker_history.columns.tolist()
    primary_factors = [f for f in ['zscore', 'rsi', 'atr', 'mfi', 'adx'] if f in available_cols]
    
    # Get the latest row that has at least SOME technical data
    valid_data = ticker_history.dropna(subset=primary_factors, how='all').iloc[0] if not primary_factors == [] else ticker_history.iloc[0]

    st.markdown(f"### 🛡️ Analysis for {ticker}")
    st.markdown('<div class="intel-card">', unsafe_allow_html=True)
    
    # MEANINGFUL ACTION LOGIC
    sig = str(valid_data.get('signal', '')).upper()
    raw_action = str(valid_data.get('suggested_action', 'WAIT')).upper()
    
    # If the theory is Bullish but action is "Stay Cash", explain it professionally
    if ("BULL" in sig or "BUY" in sig) and ("CASH" in raw_action):
        display_action = "MONITORING FOR ENTRY"
        reasoning = "Technical strength is building (Bullish Signal). Execution is paused pending volume confirmation."
    else:
        display_action = raw_action if raw_action != 'NONE' else "OBSERVING"
        reasoning = valid_data.get('execution_stance', 'Maintaining current baseline.')

    st.subheader(f"Strategy: {display_action}")
    st.info(reasoning)

    # Display Factors
    cols = st.columns(len(primary_factors) if primary_factors else 1)
    for i, factor in enumerate(primary_factors):
        val = valid_data.get(factor)
        with cols[i]:
            st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">{factor}</div>
                    <div class="metric-value">{f"{val:.2f}" if isinstance(val, (int, float)) else val}</div>
                </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("📖 Dictionary & Factor Dictionary"):
        st.write("**Z-Score:** Standard deviation from the mean. High = Overextended, Low = Undervalued.")
        st.write("**RSI:** Momentum oscillator. <30 is oversold, >70 is overbought.")
        st.json(valid_data.to_dict())
else:
    st.info("Select an asset from the matrix to load technical intelligence.")
